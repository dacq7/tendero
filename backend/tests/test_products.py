"""Tests de productos: CRUD, unicidad, margen calculado, búsqueda y permisos."""

from fastapi.testclient import TestClient


def _nuevo_producto(client: TestClient, headers: dict, **over) -> dict:
    payload = {
        "nombre": "Gaseosa 400ml",
        "sku": "SKU-001",
        "precio_costo_centavos": 120000,
        "precio_venta_centavos": 200000,
        "iva": "tarifa_19",
        "unidad": "unidad",
        "stock_minimo_milesimas": 5000,
    }
    payload.update(over)
    return client.post("/products", json=payload, headers=headers)


def test_crear_producto_calcula_margen_y_arranca_en_cero(
    client: TestClient, admin_headers: dict
) -> None:
    res = _nuevo_producto(client, admin_headers)
    assert res.status_code == 201
    p = res.json()
    assert p["stock_milesimas"] == 0  # se carga con entradas, no al crear
    assert p["margen_centavos"] == 80000  # 200000 - 120000
    assert p["margen_bps"] == 4000  # 80000/200000 = 40% = 4000 bps
    assert p["stock_bajo"] is True  # mínimo 5000 > 0 y stock 0 <= 5000


def test_sku_duplicado_da_409(client: TestClient, admin_headers: dict) -> None:
    assert _nuevo_producto(client, admin_headers).status_code == 201
    dup = _nuevo_producto(client, admin_headers, nombre="Otra")
    assert dup.status_code == 409


def test_codigo_barras_duplicado_da_409(client: TestClient, admin_headers: dict) -> None:
    _nuevo_producto(client, admin_headers, sku="A", codigo_barras="7700000000001")
    dup = _nuevo_producto(client, admin_headers, sku="B", codigo_barras="7700000000001")
    assert dup.status_code == 409


def test_varios_productos_sin_codigo_barras_conviven(
    client: TestClient, admin_headers: dict
) -> None:
    # NULL en columna UNIQUE: Postgres permite múltiples.
    assert _nuevo_producto(client, admin_headers, sku="A").status_code == 201
    assert _nuevo_producto(client, admin_headers, sku="B").status_code == 201


def test_precio_negativo_da_422(client: TestClient, admin_headers: dict) -> None:
    res = _nuevo_producto(client, admin_headers, precio_venta_centavos=-1)
    assert res.status_code == 422


def test_iva_fuera_del_enum_da_422(client: TestClient, admin_headers: dict) -> None:
    res = _nuevo_producto(client, admin_headers, iva="tarifa_8")
    assert res.status_code == 422


def test_nombre_o_sku_vacio_da_422(client: TestClient, admin_headers: dict) -> None:
    assert _nuevo_producto(client, admin_headers, nombre="").status_code == 422
    assert _nuevo_producto(client, admin_headers, sku="").status_code == 422


def test_buscar_por_barcode(client: TestClient, admin_headers: dict) -> None:
    _nuevo_producto(client, admin_headers, codigo_barras="7700000000009")
    res = client.get("/products/barcode/7700000000009", headers=admin_headers)
    assert res.status_code == 200
    assert res.json()["codigo_barras"] == "7700000000009"
    assert client.get("/products/barcode/0000", headers=admin_headers).status_code == 404


def test_patch_no_toca_stock(client: TestClient, admin_headers: dict) -> None:
    pid = _nuevo_producto(client, admin_headers).json()["id"]
    # No existe campo de stock en el update; el modelo lo ignora.
    res = client.patch(
        f"/products/{pid}",
        json={"precio_venta_centavos": 250000, "stock_milesimas": 9999},
        headers=admin_headers,
    )
    assert res.status_code == 200
    assert res.json()["precio_venta_centavos"] == 250000
    assert res.json()["stock_milesimas"] == 0  # intacto


def test_soft_delete_conserva_kardex_y_oculta_de_listado(
    client: TestClient, admin_headers: dict
) -> None:
    pid = _nuevo_producto(client, admin_headers).json()["id"]
    assert client.delete(f"/products/{pid}", headers=admin_headers).status_code == 204
    activos = client.get("/products", headers=admin_headers).json()
    assert activos == []
    todos = client.get("/products?solo_activos=false", headers=admin_headers).json()
    assert len(todos) == 1


def test_cajero_consulta_pero_no_crea(client: TestClient, cajero_headers: dict) -> None:
    assert client.get("/products", headers=cajero_headers).status_code == 200
    res = _nuevo_producto(client, cajero_headers)
    assert res.status_code == 403


def test_sin_token_no_lista(client: TestClient) -> None:
    assert client.get("/products").status_code == 401


def test_supplier_inexistente_al_crear_da_404(client: TestClient, admin_headers: dict) -> None:
    res = _nuevo_producto(client, admin_headers, supplier_id=999)
    assert res.status_code == 404
