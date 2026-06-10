"""Sesión de caja: apertura/cierre con arqueo.

Regla "una sola caja abierta a la vez" = VALIDACIÓN DE NEGOCIO en cash_service
(no un límite estructural del modelo). `user_id` registra quién abrió, de modo
que migrar a multi-caja en el futuro no exija rehacer el modelo.
"""

from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint
from sqlmodel import Field, SQLModel


class CashSessionStatus(StrEnum):
    abierta = "abierta"
    cerrada = "cerrada"


class CashRegisterSession(SQLModel, table=True):
    __tablename__ = "cash_register_sessions"
    __table_args__ = (
        CheckConstraint("monto_inicial_centavos >= 0", name="ck_cash_monto_inicial_no_neg"),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", ondelete="RESTRICT", index=True)
    status: CashSessionStatus = Field(default=CashSessionStatus.abierta, index=True)
    monto_inicial_centavos: int = Field(default=0)
    abierta_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)

    # Arqueo (null hasta cerrar).
    cerrada_at: datetime | None = Field(default=None)
    closed_by_user_id: int | None = Field(default=None, foreign_key="users.id", ondelete="SET NULL")
    efectivo_contado_centavos: int | None = Field(default=None)
    efectivo_esperado_centavos: int | None = Field(default=None)
    diferencia_centavos: int | None = Field(default=None)  # contado - esperado (+/-)
    nota_cierre: str | None = Field(default=None, max_length=500)
