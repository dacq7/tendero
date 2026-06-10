"""Tests de caja: apertura única, arqueo y permisos."""

from fastapi.testclient import TestClient

from tests.conftest import auth_headers


def test_abrir_caja(client: TestClient, cajero_headers: dict) -> None:
    res = client.post(
        "/cash/sessions", json={"monto_inicial_centavos": 5000000}, headers=cajero_headers
    )
    assert res.status_code == 201
    body = res.json()
    assert body["status"] == "abierta"
    assert body["monto_inicial_centavos"] == 5000000


def test_segunda_apertura_con_una_abierta_da_409(client: TestClient, cajero_headers: dict) -> None:
    client.post("/cash/sessions", json={"monto_inicial_centavos": 0}, headers=cajero_headers)
    res = client.post("/cash/sessions", json={"monto_inicial_centavos": 0}, headers=cajero_headers)
    assert res.status_code == 409


def test_current_devuelve_la_abierta(client: TestClient, cajero_headers: dict) -> None:
    client.post("/cash/sessions", json={"monto_inicial_centavos": 100000}, headers=cajero_headers)
    res = client.get("/cash/sessions/current", headers=cajero_headers)
    assert res.status_code == 200
    assert res.json()["status"] == "abierta"


def test_current_sin_caja_da_409(client: TestClient, cajero_headers: dict) -> None:
    assert client.get("/cash/sessions/current", headers=cajero_headers).status_code == 409


def test_cerrar_caja_sin_ventas_arqueo_cuadra(client: TestClient, cajero_headers: dict) -> None:
    cid = client.post(
        "/cash/sessions", json={"monto_inicial_centavos": 200000}, headers=cajero_headers
    ).json()["id"]
    res = client.post(
        f"/cash/sessions/{cid}/close",
        json={"efectivo_contado_centavos": 200000},
        headers=cajero_headers,
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "cerrada"
    assert body["efectivo_esperado_centavos"] == 200000
    assert body["diferencia_centavos"] == 0


def test_cerrar_caja_con_faltante(client: TestClient, cajero_headers: dict) -> None:
    cid = client.post(
        "/cash/sessions", json={"monto_inicial_centavos": 200000}, headers=cajero_headers
    ).json()["id"]
    res = client.post(
        f"/cash/sessions/{cid}/close",
        json={"efectivo_contado_centavos": 150000},
        headers=cajero_headers,
    )
    assert res.json()["diferencia_centavos"] == -50000  # faltante


def test_cerrar_caja_ya_cerrada_da_409(client: TestClient, cajero_headers: dict) -> None:
    cid = client.post(
        "/cash/sessions", json={"monto_inicial_centavos": 0}, headers=cajero_headers
    ).json()["id"]
    client.post(
        f"/cash/sessions/{cid}/close",
        json={"efectivo_contado_centavos": 0},
        headers=cajero_headers,
    )
    res = client.post(
        f"/cash/sessions/{cid}/close",
        json={"efectivo_contado_centavos": 0},
        headers=cajero_headers,
    )
    assert res.status_code == 409


def test_cajero_no_cierra_caja_de_otro(
    client: TestClient, admin_user, cajero_headers: dict
) -> None:
    # admin abre su caja; el cajero intenta cerrarla.
    admin_h = auth_headers(client, "admin@test.co", "Test1234!")
    cid = client.post("/cash/sessions", json={"monto_inicial_centavos": 0}, headers=admin_h).json()[
        "id"
    ]
    res = client.post(
        f"/cash/sessions/{cid}/close",
        json={"efectivo_contado_centavos": 0},
        headers=cajero_headers,
    )
    assert res.status_code == 403


def test_cajero_no_ve_detalle_de_caja_de_otro(
    client: TestClient, admin_user, cajero_headers: dict
) -> None:
    admin_h = auth_headers(client, "admin@test.co", "Test1234!")
    cid = client.post(
        "/cash/sessions", json={"monto_inicial_centavos": 0}, headers=admin_h
    ).json()["id"]
    # El cajero intenta ver el detalle de la caja del admin.
    assert client.get(f"/cash/sessions/{cid}", headers=cajero_headers).status_code == 403


def test_sin_token_no_abre_caja(client: TestClient) -> None:
    assert client.post("/cash/sessions", json={"monto_inicial_centavos": 0}).status_code == 401
