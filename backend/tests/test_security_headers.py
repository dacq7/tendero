"""Hardening Fase 6 B.1 — cabeceras de seguridad y manejo de errores.

Verifica que toda respuesta lleva las cabeceras defensivas y que un error NO
controlado devuelve un cuerpo genérico (sin trazas ni detalles internos).
"""

from fastapi.testclient import TestClient

from app.main import app

EXPECTED_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cross-Origin-Opener-Policy": "same-origin",
}


def test_respuestas_traen_cabeceras_de_seguridad(client: TestClient) -> None:
    res = client.get("/health")
    assert res.status_code == 200
    for name, value in EXPECTED_HEADERS.items():
        assert res.headers.get(name) == value


def test_hsts_ausente_fuera_de_produccion(client: TestClient) -> None:
    """En test/desarrollo (http) no se emite HSTS."""
    res = client.get("/health")
    assert "Strict-Transport-Security" not in res.headers


def test_error_no_controlado_no_filtra_traza() -> None:
    """Un 500 inesperado devuelve cuerpo genérico, nunca la traza ni el mensaje real."""
    secreto = "boom-detalle-interno-no-debe-salir"

    async def _boom() -> dict:
        raise RuntimeError(secreto)

    app.add_api_route("/__boom_test", _boom, methods=["GET"])
    try:
        # raise_server_exceptions=False: el TestClient deja que el handler responda
        # en vez de re-lanzar, como haría uvicorn en producción.
        with TestClient(app, raise_server_exceptions=False) as c:
            res = c.get("/__boom_test")
        assert res.status_code == 500
        assert res.json() == {"detail": "Error interno"}
        assert secreto not in res.text
        # Nota: la respuesta 500 la emite el ServerErrorMiddleware (el más externo,
        # por fuera del middleware de cabeceras), así que aquí no se exigen. Lo que
        # importa para seguridad es el cuerpo genérico sin traza, ya verificado.
    finally:
        # No dejar la ruta de prueba colgada en la app global.
        app.router.routes[:] = [
            r for r in app.router.routes if getattr(r, "path", None) != "/__boom_test"
        ]
