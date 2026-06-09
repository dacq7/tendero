"""Tests de proveedores: CRUD, soft-delete y permisos por rol."""

from fastapi.testclient import TestClient


def test_admin_crea_y_lista_proveedor(client: TestClient, admin_headers: dict) -> None:
    res = client.post(
        "/suppliers",
        json={"nombre": "Distribuidora La 14", "nit": "900123456-1"},
        headers=admin_headers,
    )
    assert res.status_code == 201
    creado = res.json()
    assert creado["id"]
    assert creado["nombre"] == "Distribuidora La 14"
    assert creado["activo"] is True

    listado = client.get("/suppliers", headers=admin_headers).json()
    assert len(listado) == 1


def test_cajero_consulta_pero_no_crea(client: TestClient, cajero_headers: dict) -> None:
    # Lectura permitida
    assert client.get("/suppliers", headers=cajero_headers).status_code == 200
    # Escritura prohibida
    res = client.post("/suppliers", json={"nombre": "Prohibido"}, headers=cajero_headers)
    assert res.status_code == 403


def test_sin_token_no_lista(client: TestClient) -> None:
    assert client.get("/suppliers").status_code == 401


def test_actualizar_proveedor(client: TestClient, admin_headers: dict) -> None:
    sid = client.post("/suppliers", json={"nombre": "Inicial"}, headers=admin_headers).json()["id"]
    res = client.patch(f"/suppliers/{sid}", json={"telefono": "3001234567"}, headers=admin_headers)
    assert res.status_code == 200
    assert res.json()["telefono"] == "3001234567"
    assert res.json()["nombre"] == "Inicial"


def test_soft_delete_excluye_de_listado_por_defecto(
    client: TestClient, admin_headers: dict
) -> None:
    sid = client.post("/suppliers", json={"nombre": "Temporal"}, headers=admin_headers).json()["id"]
    assert client.delete(f"/suppliers/{sid}", headers=admin_headers).status_code == 204

    activos = client.get("/suppliers", headers=admin_headers).json()
    assert activos == []
    con_inactivos = client.get("/suppliers?solo_activos=false", headers=admin_headers).json()
    assert len(con_inactivos) == 1
    assert con_inactivos[0]["activo"] is False


def test_proveedor_inexistente_da_404(client: TestClient, admin_headers: dict) -> None:
    assert client.get("/suppliers/999", headers=admin_headers).status_code == 404


def test_email_invalido_da_422(client: TestClient, admin_headers: dict) -> None:
    res = client.post(
        "/suppliers",
        json={"nombre": "X", "email": "no-es-email"},
        headers=admin_headers,
    )
    assert res.status_code == 422
