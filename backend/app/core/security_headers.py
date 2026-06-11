"""Cabeceras de seguridad para todas las respuestas de la API (Fase 6 B.1).

La API sirve JSON, no HTML, así que la CSP es responsabilidad del frontend (Next).
Aquí se añaden las cabeceras defensivas que sí aplican a una API:

- `X-Content-Type-Options: nosniff` — impide el MIME sniffing.
- `X-Frame-Options: DENY` — la API nunca debe embeberse en un frame.
- `Referrer-Policy: no-referrer` — no filtrar URLs internas como referer.
- `Cross-Origin-Opener-Policy: same-origin` — aísla el contexto de navegación.
- `Strict-Transport-Security` — SOLO en producción (en local se usa http).
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_BASE_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cross-Origin-Opener-Policy": "same-origin",
}

# Un año, con subdominios. Solo tiene sentido tras TLS (producción).
_HSTS = "max-age=31536000; includeSubDomains"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, is_production: bool) -> None:
        super().__init__(app)
        self._is_production = is_production

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        for name, value in _BASE_HEADERS.items():
            response.headers.setdefault(name, value)
        if self._is_production:
            response.headers.setdefault("Strict-Transport-Security", _HSTS)
        return response
