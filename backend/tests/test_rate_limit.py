"""Hardening Fase 6 B.1 — rate limiting en endpoints sensibles.

Login (anti fuerza bruta) y webhook (anti flood) devuelven 429 al superar el límite
por IP. El estado se resetea entre tests vía el fixture autouse de conftest.
"""

from fastapi.testclient import TestClient

from app.core.rate_limit import login_limiter, webhook_limiter


def test_login_excedido_da_429(client: TestClient) -> None:
    """Tras `max_events` intentos, el siguiente login desde la misma IP da 429."""
    cuerpo = {"email": "noexiste@test.co", "password": "malo"}
    # Los primeros N intentos fallan con 401 (credenciales), no con 429.
    for _ in range(login_limiter.max_events):
        res = client.post("/auth/login", json=cuerpo)
        assert res.status_code == 401
    # El intento N+1 se corta por rate limit.
    bloqueado = client.post("/auth/login", json=cuerpo)
    assert bloqueado.status_code == 429


def test_webhook_excedido_da_429(client: TestClient) -> None:
    """El webhook público corta el flood con 429 (antes de procesar firma)."""
    # Payloads basura: sin rate limit darían 400 (firma inválida). Con el límite,
    # tras `max_events` el siguiente es 429.
    for _ in range(webhook_limiter.max_events):
        res = client.post("/webhooks/wompi", json={"basura": True})
        assert res.status_code == 400
    bloqueado = client.post("/webhooks/wompi", json={"basura": True})
    assert bloqueado.status_code == 429


def test_limiter_unidad_ventana_deslizante() -> None:
    """El limitador puro: cuenta en la ventana y olvida lo viejo (con `now` inyectado)."""
    from app.core.rate_limit import InMemoryRateLimiter

    lim = InMemoryRateLimiter(max_events=2, window_s=10)
    assert lim.allow("k", now=0.0) is True
    assert lim.allow("k", now=1.0) is True
    assert lim.allow("k", now=2.0) is False  # tercer evento dentro de la ventana
    # Pasada la ventana, vuelve a permitir.
    assert lim.allow("k", now=12.0) is True


def test_limiter_acota_memoria_con_tope_de_claves() -> None:
    """El mapa de IPs no crece sin límite: al saturarse, purga expiradas o rechaza."""
    from app.core.rate_limit import InMemoryRateLimiter

    lim = InMemoryRateLimiter(max_events=5, window_s=10)
    lim._MAX_KEYS = 2  # tope bajo para el test
    assert lim.allow("ip-a", now=0.0) is True
    assert lim.allow("ip-b", now=0.0) is True
    # Mapa lleno y las claves siguen vigentes (ventana 10): una IP NUEVA se rechaza.
    assert lim.allow("ip-c", now=1.0) is False
    # Pasada la ventana de a/b, se purgan y la nueva IP entra.
    assert lim.allow("ip-c", now=20.0) is True
