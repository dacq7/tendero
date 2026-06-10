"""Emisión fiscal de una factura: documento electrónico transmitido al PT/DIAN.

1:1 con Invoice (UNIQUE(invoice_id) = candado de idempotencia, espejo de Payment).
Guarda el número fiscal (del rango de la resolución), CUFE, estado, motivo de
rechazo e intentos. `Invoice.dian_status`/`cufe` son una caché para listados.
"""

from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel

from app.models.invoice import DianStatus


class FiscalProvider(StrEnum):
    mock = "mock"
    pt = "pt"  # Proveedor Tecnológico real (Alanube/Factus…)


class FiscalEmission(SQLModel, table=True):
    __tablename__ = "fiscal_emissions"
    __table_args__ = (
        UniqueConstraint("invoice_id", name="uq_fiscal_emissions_invoice"),
        UniqueConstraint("resolution_id", "numero_fiscal", name="uq_fiscal_emissions_res_numero"),
        UniqueConstraint("numero_fiscal_completo", name="uq_fiscal_emissions_numero"),
    )

    id: int | None = Field(default=None, primary_key=True)
    invoice_id: int = Field(foreign_key="invoices.id", ondelete="RESTRICT", index=True)
    resolution_id: int = Field(
        foreign_key="invoice_resolutions.id", ondelete="RESTRICT", index=True
    )

    prefijo: str = Field(max_length=10)
    numero_fiscal: int
    numero_fiscal_completo: str = Field(max_length=40)  # p. ej. "SETP990000001"

    provider: FiscalProvider
    status: DianStatus  # pending | accepted | rejected (none solo en Invoice)
    cufe: str | None = Field(default=None, max_length=255)
    pt_document_id: str | None = Field(default=None, max_length=255)
    motivo_rechazo: str | None = Field(default=None, max_length=500)
    intentos: int = Field(default=0)

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        nullable=False,
        sa_column_kwargs={"onupdate": lambda: datetime.now(UTC)},
    )
