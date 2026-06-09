"""Tests del flujo de autenticación end-to-end contra la base de test."""

from fastapi.testclient import TestClient

from app.models.user import User
from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD


def _login(client: TestClient, email: str, password: str):
    return client.post("/auth/login", json={"email": email, "password": password})


def test_login_ok_devuelve_tokens(client: TestClient, admin_user: User) -> None:
    res = _login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    assert res.status_code == 200
    body = res.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "bearer"


def test_login_password_invalida_da_401(client: TestClient, admin_user: User) -> None:
    res = _login(client, ADMIN_EMAIL, "incorrecta")
    assert res.status_code == 401


def test_login_email_desconocido_da_401(client: TestClient) -> None:
    res = _login(client, "nadie@test.co", ADMIN_PASSWORD)
    assert res.status_code == 401


def test_me_con_token_devuelve_usuario(client: TestClient, admin_user: User) -> None:
    token = _login(client, ADMIN_EMAIL, ADMIN_PASSWORD).json()["access_token"]
    res = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    body = res.json()
    assert body["email"] == ADMIN_EMAIL
    assert body["role"] == "admin"


def test_me_sin_token_da_401(client: TestClient) -> None:
    res = client.get("/auth/me")
    assert res.status_code == 401


def test_me_con_token_basura_da_401(client: TestClient) -> None:
    res = client.get("/auth/me", headers={"Authorization": "Bearer no-es-un-jwt"})
    assert res.status_code == 401


def test_userread_nunca_expone_hashed_password(client: TestClient, admin_user: User) -> None:
    token = _login(client, ADMIN_EMAIL, ADMIN_PASSWORD).json()["access_token"]
    res = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    body = res.json()
    assert "hashed_password" not in body
    assert "password" not in body
