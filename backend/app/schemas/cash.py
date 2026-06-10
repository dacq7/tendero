"""DTOs de caja. Dinero en centavos."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.cash_register_session import CashSessionStatus


class CashSessionOpen(BaseModel):
    monto_inicial_centavos: int = Field(ge=0)


class CashSessionClose(BaseModel):
    efectivo_contado_centavos: int = Field(ge=0)
    nota_cierre: str | None = Field(default=None, max_length=500)


class CashSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    status: CashSessionStatus
    monto_inicial_centavos: int
    abierta_at: datetime
    cerrada_at: datetime | None
    closed_by_user_id: int | None
    efectivo_contado_centavos: int | None
    efectivo_esperado_centavos: int | None
    diferencia_centavos: int | None
    nota_cierre: str | None


class CashSessionDetail(CashSessionRead):
    """Detalle con el resumen de ventas pagadas por método (arqueo informativo)."""

    totales_por_metodo: dict[str, int]
