"""Selección del proveedor fiscal por env var (FISCAL_PROVIDER=mock|real).

Sin caché: se lee `settings` en cada llamada (barato) para no congelar el
proveedor entre tests ni ante cambios de env var.
"""

from app.core.config import settings
from app.services.fiscal.mock import MockFiscalProvider
from app.services.fiscal.provider import FiscalGateway
from app.services.fiscal.real import RealFiscalProvider


def get_fiscal_provider() -> FiscalGateway:
    if settings.fiscal_provider == "real":
        return RealFiscalProvider()
    return MockFiscalProvider()


def is_mock() -> bool:
    return settings.fiscal_provider != "real"
