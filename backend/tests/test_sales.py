"""Tests de ventas: atomicidad, snapshot, IVA/totales, caja obligatoria, permisos."""

from fastapi.testclient import TestClient


def crear_producto_con_stock(
    client: TestClient,
    admin_headers: dict,
    *,
    sku: str,
    precio_venta_centavos: int = 100000,
    iva: str = "tarifa_19",
    stock_milesimas: int = 10000,
) -> int:
    """Crea un producto (admin) y le carga stock con una entrada de mercancía."""
    pid = client.post(
        "/products",
        json={
            "nombre": f"Producto {sku}",
            "sku": sku,
            "precio_venta_centavos": precio_venta_centavos,
            "precio_costo_centavos": 50000,
            "iva": iva,
        },
        headers=admin_headers,
    ).json()["id"]
    client.post(
        "/inventory/entries",
        json={
            "lineas": [
                {
                    "product_id": pid,
                    "cantidad_milesimas": stock_milesimas,
                    "costo_unitario_centavos": 50000,
                }
            ]
        },
        headers=admin_headers,
    )
    return pid


def abrir_caja(client: TestClient, headers: dict, monto: int = 0) -> int:
    return client.post(
        "/cash/sessions", json={"monto_inicial_centavos": monto}, headers=headers
    ).json()["id"]


def vender(client: TestClient, headers: dict, *lineas: tuple[int, int], metodo: str = "efectivo"):
    """POST /sales. `lineas` son tuplas (product_id, cantidad_milesimas)."""
    payload = {
        "lineas": [{"product_id": pid, "cantidad_milesimas": qty} for pid, qty in lineas],
        "metodo_pago": metodo,
    }
    return client.post("/sales", json=payload, headers=headers)


def test_venta_feliz_descuenta_stock_y_factura(client: TestClient, admin_headers: dict) -> None:
    pid = crear_producto_con_stock(client, admin_headers, sku="V1", stock_milesimas=10000)
    abrir_caja(client, admin_headers)
    res = vender(client, admin_headers, (pid, 3000))
    assert res.status_code == 201
    sale = res.json()
    assert sale["status"] == "pagada"
    assert sale["subtotal_centavos"] == 300000  # 100000 * 3
    assert sale["iva_total_centavos"] == 57000  # 19%
    assert sale["total_centavos"] == 357000
    assert sale["invoice"]["numero_completo"] == "POS-000001"
    assert sale["items"][0]["cantidad_milesimas"] == 3000
    p = client.get(f"/products/{pid}", headers=admin_headers).json()
    assert p["stock_milesimas"] == 7000  # descontado


def test_snapshot_inmutable_ante_cambio_de_precio(client: TestClient, admin_headers: dict) -> None:
    pid = crear_producto_con_stock(client, admin_headers, sku="V2", precio_venta_centavos=100000)
    abrir_caja(client, admin_headers)
    sale_id = vender(client, admin_headers, (pid, 1000)).json()["id"]
    # Cambiar precio y nombre del producto DESPUÉS de vender.
    client.patch(
        f"/products/{pid}",
        json={"precio_venta_centavos": 999999, "nombre": "Renombrado"},
        headers=admin_headers,
    )
    item = client.get(f"/sales/{sale_id}", headers=admin_headers).json()["items"][0]
    assert item["precio_unitario_centavos"] == 100000  # snapshot viejo
    assert item["nombre_snapshot"] == "Producto V2"


def test_venta_atomica_rollback_si_una_linea_excede_stock(
    client: TestClient, admin_headers: dict
) -> None:
    p1 = crear_producto_con_stock(client, admin_headers, sku="A1", stock_milesimas=5000)
    p2 = crear_producto_con_stock(client, admin_headers, sku="A2", stock_milesimas=1000)
    abrir_caja(client, admin_headers)
    res = vender(client, admin_headers, (p1, 3000), (p2, 5000))  # 2ª excede
    assert res.status_code == 409
    # Rollback total: stock de p1 intacto, sin factura, número NO consumido.
    assert client.get(f"/products/{p1}", headers=admin_headers).json()["stock_milesimas"] == 5000
    assert client.get("/invoices", headers=admin_headers).json() == []
    # La siguiente venta válida toma el número 1 (no hubo hueco).
    ok = vender(client, admin_headers, (p1, 1000))
    assert ok.json()["invoice"]["numero_completo"] == "POS-000001"


def test_venta_sin_caja_abierta_da_409(client: TestClient, admin_headers: dict) -> None:
    pid = crear_producto_con_stock(client, admin_headers, sku="NC", stock_milesimas=5000)
    assert vender(client, admin_headers, (pid, 1000)).status_code == 409


def test_iva_mixto_totales(client: TestClient, admin_headers: dict) -> None:
    grav = crear_producto_con_stock(
        client, admin_headers, sku="G", precio_venta_centavos=100000, iva="tarifa_19"
    )
    exento = crear_producto_con_stock(
        client, admin_headers, sku="E", precio_venta_centavos=200000, iva="exento"
    )
    abrir_caja(client, admin_headers)
    sale = vender(client, admin_headers, (grav, 1000), (exento, 1000), metodo="tarjeta").json()
    assert sale["subtotal_centavos"] == 300000  # 100000 + 200000
    assert sale["iva_total_centavos"] == 19000  # solo el gravado
    assert sale["total_centavos"] == 319000


def test_stock_insuficiente_da_409(client: TestClient, admin_headers: dict) -> None:
    pid = crear_producto_con_stock(client, admin_headers, sku="SI", stock_milesimas=1000)
    abrir_caja(client, admin_headers)
    assert vender(client, admin_headers, (pid, 9000)).status_code == 409


def test_venta_vacia_da_422(client: TestClient, admin_headers: dict) -> None:
    abrir_caja(client, admin_headers)
    res = client.post(
        "/sales", json={"lineas": [], "metodo_pago": "efectivo"}, headers=admin_headers
    )
    assert res.status_code == 422


def test_cajero_ve_solo_sus_ventas(
    client: TestClient, admin_headers: dict, cajero_headers: dict
) -> None:
    pid = crear_producto_con_stock(client, admin_headers, sku="SH", stock_milesimas=10000)
    # Admin abre caja, vende y cierra.
    admin_caja = abrir_caja(client, admin_headers)
    vender(client, admin_headers, (pid, 1000))
    client.post(
        f"/cash/sessions/{admin_caja}/close",
        json={"efectivo_contado_centavos": 0},
        headers=admin_headers,
    )
    # Cajero abre su caja y vende.
    abrir_caja(client, cajero_headers)
    vender(client, cajero_headers, (pid, 1000))
    assert len(client.get("/sales", headers=cajero_headers).json()) == 1  # solo la suya
    assert len(client.get("/sales", headers=admin_headers).json()) == 2  # todas


def test_sin_token_no_vende(client: TestClient) -> None:
    assert client.post("/sales", json={"lineas": [], "metodo_pago": "efectivo"}).status_code == 401
