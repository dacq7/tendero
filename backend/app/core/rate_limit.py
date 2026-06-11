"""Rate limiting básico en memoria (Fase 6 B.1).

Limitador por IP con ventana deslizante, suficiente para un despliegue de portafolio
mono-instancia (Railway/Vercel). En un despliegue multi-instancia real, el estado se
movería a un backend compartido (p. ej. Redis); la interfaz de la dependencia no
cambiaría. Solo se aplica a endpoints sensibles: login (anti fuerza bruta) y el
webhook público (anti flood).

Nota sobre la IP tras proxy: en Railway/Vercel el PaaS añade la IP real del cliente
como el ÚLTIMO salto de `X-Forwarded-For` (los saltos anteriores los puede falsear el
cliente). Por eso se toma el último, no el primero: así un cliente no puede evadir el
límite inyectando IPs falsas al principio de la cabecera. Sin proxy, se usa la IP de
la conexión. Para un límite básico mono-instancia es suficiente.
"""

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status


class InMemoryRateLimiter:
    """Cuenta eventos por clave en una ventana deslizante. No es thread-safe a nivel
    de microsegundo, pero para un límite defensivo basta (el peor caso es contar uno
    de más o de menos en una carrera)."""

    # Tope de claves distintas (IPs) para acotar la memoria: sin él, un atacante que
    # rote IPs haría crecer el mapa sin límite. Al llenarse, se purgan las claves cuya
    # ventana ya expiró; si aun así está lleno, se rechaza la IP NUEVA (fail-closed).
    _MAX_KEYS = 50_000

    def __init__(self, *, max_events: int, window_s: float) -> None:
        self.max_events = max_events
        self.window_s = window_s
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def _evict_expired(self, now: float) -> None:
        cutoff = now - self.window_s
        muertas = [k for k, dq in self._hits.items() if not dq or dq[-1] <= cutoff]
        for k in muertas:
            del self._hits[k]

    def allow(self, key: str, *, now: float | None = None) -> bool:
        """Registra un intento. Devuelve False si supera el límite en la ventana."""
        now = time.monotonic() if now is None else now
        cutoff = now - self.window_s
        if key not in self._hits and len(self._hits) >= self._MAX_KEYS:
            self._evict_expired(now)
            if len(self._hits) >= self._MAX_KEYS:
                return False  # mapa saturado: no admitir IPs nuevas (fail-closed)
        dq = self._hits[key]
        while dq and dq[0] <= cutoff:
            dq.popleft()
        if len(dq) >= self.max_events:
            return False
        dq.append(now)
        return True

    def reset(self) -> None:
        """Limpia todo el estado (usado por la suite de tests entre casos)."""
        self._hits.clear()


# Singletons por endpoint sensible. Valores conservadores para no molestar al uso
# legítimo pero cortar abuso evidente.
login_limiter = InMemoryRateLimiter(max_events=10, window_s=300)  # 10 / 5 min / IP
webhook_limiter = InMemoryRateLimiter(max_events=60, window_s=60)  # 60 / min / IP


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # Último salto = IP añadida por el proxy de confianza del PaaS (ver módulo).
        return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


def rate_limit(limiter: InMemoryRateLimiter, scope: str):
    """Crea una dependencia FastAPI que aplica `limiter` por IP bajo `scope`."""

    def dependency(request: Request) -> None:
        key = f"{scope}:{_client_ip(request)}"
        if not limiter.allow(key):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Demasiadas solicitudes; intenta de nuevo más tarde.",
            )

    return dependency
