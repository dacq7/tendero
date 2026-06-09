"""Tests del kardex: stock, costeo CMP, atomicidad, alertas y permisos.

Cobertura crítica: todo lo que toca stock o dinero.
"""

from fastapi.testclient import TestClient


def _crear_producto(client: TestClient, headers: dict, **over) -> int:
    payload = {
        "nombre": "Arroz 1kg",
        "sku": "ARZ-001",
        "precio_costo_centavos": 100000,
        "precio_venta_centavos": 150000,
        "stock_minimo_milesimas": 3000,
    }
    payload.update(over)
    return client.post("/products", json=payload, headers=headers).json()["id"]


def _movimiento(client: TestClient, headers: dict, **body) -> object:
    return client.post("/inventory/movements", json=body, headers=headers)


def _stock(client: TestClient, headers: dict, pid: int) -> int:
    return client.get(f"/products/{pid}", headers=headers).json()["stock_milesimas"]


# ---------- Stock: entrada / salida / merma ----------


def test_entrada_suma_stock_y_registra_kardex(client: TestClient, admin_headers: dict) -> None:
    pid = _crear_producto(client, admin_headers)
    res = _movimiento(
        client,
        admin_headers,
        product_id=pid,
        tipo="entrada",
        cantidad_milesimas=10000,
        costo_unitario_centavos=100000,
    )
    assert res.status_code == 201
    mov = res.json()
    assert mov["stock_resultante_milesimas"] == 10000
    assert mov["user_id"]  # auditoría: quién lo hizo
    assert _stock(client, admin_headers, pid) == 10000


def test_salida_y_merma_restan_stock(client: TestClient, admin_headers: dict) -> None:
    pid = _crear_producto(client, admin_headers)
    _movimiento(
        client,
        admin_headers,
        product_id=pid,
        tipo="entrada",
        cantidad_milesimas=10000,
        costo_unitario_centavos=100000,
    )
    _movimiento(client, admin_headers, product_id=pid, tipo="salida", cantidad_milesimas=3000)
    assert _stock(client, admin_headers, pid) == 7000
    _movimiento(client, admin_headers, product_id=pid, tipo="merma", cantidad_milesimas=1000)
    assert _stock(client, admin_headers, pid) == 6000


def test_salida_excede_stock_da_409_y_no_muta(client: TestClient, admin_headers: dict) -> None:
    pid = _crear_producto(client, admin_headers)
    _movimiento(
        client,
        admin_headers,
        product_id=pid,
        tipo="entrada",
        cantidad_milesimas=5000,
        costo_unitario_centavos=100000,
    )
    res = _movimiento(client, admin_headers, product_id=pid, tipo="salida", cantidad_milesimas=9000)
    assert res.status_code == 409
    assert _stock(client, admin_headers, pid) == 5000  # rollback: intacto


def test_entrada_sin_costo_da_422(client: TestClient, admin_headers: dict) -> None:
    pid = _crear_producto(client, admin_headers)
    res = _movimiento(
        client, admin_headers, product_id=pid, tipo="entrada", cantidad_milesimas=1000
    )
    assert res.status_code == 422


def test_cantidad_cero_da_422(client: TestClient, admin_headers: dict) -> None:
    pid = _crear_producto(client, admin_headers)
    res = _movimiento(client, admin_headers, product_id=pid, tipo="salida", cantidad_milesimas=0)
    assert res.status_code == 422


def test_ajuste_fija_stock_objetivo(client: TestClient, admin_headers: dict) -> None:
    pid = _crear_producto(client, admin_headers)
    _movimiento(
        client,
        admin_headers,
        product_id=pid,
        tipo="entrada",
        cantidad_milesimas=10000,
        costo_unitario_centavos=100000,
    )
    res = _movimiento(
        client,
        admin_headers,
        product_id=pid,
        tipo="ajuste",
        cantidad_milesimas=8000,
        motivo="conteo físico",
    )
    assert res.status_code == 201
    assert res.json()["stock_resultante_milesimas"] == 8000
    assert res.json()["cantidad_milesimas"] == 2000  # magnitud del delta
    assert _stock(client, admin_headers, pid) == 8000


# ---------- Costeo CMP ----------


def test_entrada_actualiza_costo_promedio_ponderado(
    client: TestClient, admin_headers: dict
) -> None:
    pid = _crear_producto(client, admin_headers, precio_costo_centavos=100000)
    # 1ª entrada: 10 u a $1000 → costo queda 100000
    _movimiento(
        client,
        admin_headers,
        product_id=pid,
        tipo="entrada",
        cantidad_milesimas=10000,
        costo_unitario_centavos=100000,
    )
    # 2ª entrada: 10 u a $1400 → CMP = 120000
    _movimiento(
        client,
        admin_headers,
        product_id=pid,
        tipo="entrada",
        cantidad_milesimas=10000,
        costo_unitario_centavos=140000,
    )
    p = client.get(f"/products/{pid}", headers=admin_headers).json()
    assert p["precio_costo_centavos"] == 120000
    assert p["stock_milesimas"] == 20000
    assert p["margen_centavos"] == 30000  # 150000 - 120000


# ---------- Entrada de mercancía (atómica) ----------


def test_entrada_mercancia_multilinea(client: TestClient, admin_headers: dict) -> None:
    p1 = _crear_producto(client, admin_headers, sku="P1")
    p2 = _crear_producto(client, admin_headers, sku="P2")
    res = client.post(
        "/inventory/entries",
        json={
            "supplier_id": None,
            "lineas": [
                {"product_id": p1, "cantidad_milesimas": 5000, "costo_unitario_centavos": 100000},
                {"product_id": p2, "cantidad_milesimas": 3000, "costo_unitario_centavos": 80000},
            ],
        },
        headers=admin_headers,
    )
    assert res.status_code == 201
    assert len(res.json()["movimientos"]) == 2
    assert _stock(client, admin_headers, p1) == 5000
    assert _stock(client, admin_headers, p2) == 3000


def test_entrada_mercancia_es_atomica(client: TestClient, admin_headers: dict) -> None:
    p1 = _crear_producto(client, admin_headers, sku="P1")
    res = client.post(
        "/inventory/entries",
        json={
            "lineas": [
                {"product_id": p1, "cantidad_milesimas": 5000, "costo_unitario_centavos": 100000},
                {"product_id": 999, "cantidad_milesimas": 1000, "costo_unitario_centavos": 5000},
            ],
        },
        headers=admin_headers,
    )
    assert res.status_code == 404
    # La 1ª línea NO se aplicó: atomicidad.
    assert _stock(client, admin_headers, p1) == 0


# ---------- Alertas de stock bajo ----------


def test_alerta_stock_bajo(client: TestClient, admin_headers: dict) -> None:
    _crear_producto(client, admin_headers, sku="BAJO", stock_minimo_milesimas=5000)
    alto = _crear_producto(client, admin_headers, sku="ALTO", stock_minimo_milesimas=1000)
    # 'alto' recibe stock por encima del mínimo; 'bajo' se queda en 0.
    _movimiento(
        client,
        admin_headers,
        product_id=alto,
        tipo="entrada",
        cantidad_milesimas=10000,
        costo_unitario_centavos=50000,
    )
    alertas = client.get("/inventory/alerts/low-stock", headers=admin_headers).json()
    skus = {a["sku"] for a in alertas}
    assert "BAJO" in skus
    assert "ALTO" not in skus
    alerta_bajo = next(a for a in alertas if a["sku"] == "BAJO")
    assert alerta_bajo["faltante_milesimas"] == 5000


def test_minimo_cero_no_genera_alerta(client: TestClient, admin_headers: dict) -> None:
    # Mínimo 0 = "sin control de mínimo": no debe aparecer en alertas aunque stock=0.
    _crear_producto(client, admin_headers, sku="SINMIN", stock_minimo_milesimas=0)
    alertas = client.get("/inventory/alerts/low-stock", headers=admin_headers).json()
    assert alertas == []


# ---------- Permisos ----------


def test_cajero_no_crea_entrada_mercancia(client: TestClient, cajero_headers: dict) -> None:
    res = client.post(
        "/inventory/entries",
        json={
            "lineas": [
                {"product_id": 1, "cantidad_milesimas": 1000, "costo_unitario_centavos": 100}
            ]
        },
        headers=cajero_headers,
    )
    assert res.status_code == 403


def test_cajero_no_registra_movimiento(client: TestClient, cajero_headers: dict) -> None:
    # El cajero ni siquiera puede crear el producto; probamos el guard del endpoint.
    res = _movimiento(
        client,
        cajero_headers,
        product_id=1,
        tipo="entrada",
        cantidad_milesimas=1000,
        costo_unitario_centavos=1000,
    )
    assert res.status_code == 403


def test_cajero_consulta_alertas(
    client: TestClient, admin_headers: dict, cajero_headers: dict
) -> None:
    _crear_producto(client, admin_headers, sku="X", stock_minimo_milesimas=1000)
    assert client.get("/inventory/alerts/low-stock", headers=cajero_headers).status_code == 200


def test_kardex_lista_movimientos(client: TestClient, admin_headers: dict) -> None:
    pid = _crear_producto(client, admin_headers)
    _movimiento(
        client,
        admin_headers,
        product_id=pid,
        tipo="entrada",
        cantidad_milesimas=5000,
        costo_unitario_centavos=100000,
    )
    _movimiento(client, admin_headers, product_id=pid, tipo="salida", cantidad_milesimas=2000)
    kardex = client.get(f"/products/{pid}/kardex", headers=admin_headers).json()
    assert len(kardex) == 2
    # Orden descendente por fecha: el último (salida) primero.
    assert kardex[0]["tipo"] == "salida"
    assert kardex[0]["stock_resultante_milesimas"] == 3000
