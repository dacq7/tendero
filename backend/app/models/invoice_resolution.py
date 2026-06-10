"""Resolución de numeración DIAN del comercio (Resolución 165/2023).

La DIAN entrega un prefijo y un rango [desde, hasta] con vigencia. El número
fiscal se asigna AL EMITIR, consumiendo del rango con `last_numero` (contador sin
huecos por resolución, vía SELECT ... FOR UPDATE). Es independiente del
consecutivo POS interno (Fase 2). Regla: a lo sumo UNA resolución activa.
"""

from datetime import UTC, date, datetime

from sqlalchemy import CheckConstraint, Index, text
from sqlmodel import Field, SQLModel


class InvoiceResolution(SQLModel, table=True):
    __tablename__ = "invoice_resolutions"
    __table_args__ = (
        CheckConstraint("numero_hasta >= numero_desde", name="ck_resolution_rango"),
        CheckConstraint("last_numero >= numero_desde - 1", name="ck_resolution_last"),
        # A lo sumo una resolución activa (índice único parcial).
        Index(
            "uq_resolution_activa",
            "activa",
            unique=True,
            postgresql_where=text("activa"),
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    numero_resolucion: str = Field(max_length=64)  # el oficio DIAN
    prefijo: str = Field(max_length=10)
    numero_desde: int
    numero_hasta: int
    last_numero: int  # = numero_desde - 1 al crear; último consumido
    vigencia_desde: date
    vigencia_hasta: date
    rut_nit: str = Field(max_length=32)
    responsabilidad: str = Field(default="52", max_length=8)
    activa: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)
