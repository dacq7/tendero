"""Selección del proveedor de pagos por env var (WOMPI_PROVIDER=mock|real).

Sin caché: el proveedor se construye leyendo `settings` en cada llamada (es barato)
para que un cambio de env var surta efecto sin reiniciar y para no congelar el
proveedor entre tests.
"""

from app.core.config import settings
from app.services.payments.mock import MockWompiProvider
from app.services.payments.provider import WompiProvider
from app.services.payments.real import RealWompiProvider


def get_wompi_provider() -> WompiProvider:
    if settings.wompi_provider == "real":
        return RealWompiProvider()
    return MockWompiProvider()


def is_mock() -> bool:
    return settings.wompi_provider != "real"
