"""Factura interna: una por venta, con numeración secuencial propia.

`dian_status=none` y `cufe=null` en Fase 2 (la emisión fiscal real es Fase 4).
`wompi_transaction_id` existe pero queda null hasta Fase 3.
"""

from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.models.sale import PaymentMethod


class DianStatus(StrEnum):
    none = "none"  # sin emisión fiscal (Fase 2)
    pending = "pending"  # enviada al PT (Fase 4)
    accepted = "accepted"
    rejected = "rejected"


class Invoice(SQLModel, table=True):
    __tablename__ = "invoices"
    __table_args__ = (
        UniqueConstraint("sale_id", name="uq_invoices_sale"),  # 1 factura por venta
        UniqueConstraint("serie", "numero", name="uq_invoices_serie_numero"),
        UniqueConstraint("numero_completo", name="uq_invoices_numero_completo"),
        CheckConstraint("subtotal_centavos >= 0", name="ck_invoices_subtotal_no_neg"),
        CheckConstraint("iva_total_centavos >= 0", name="ck_invoices_iva_no_neg"),
        CheckConstraint("total_centavos >= 0", name="ck_invoices_total_no_neg"),
    )

    id: int | None = Field(default=None, primary_key=True)
    sale_id: int = Field(foreign_key="sales.id", ondelete="RESTRICT", index=True)

    serie: str = Field(default="POS", max_length=20)
    numero: int
    numero_completo: str = Field(max_length=40, index=True)  # ej. "POS-000001"

    subtotal_centavos: int
    iva_total_centavos: int
    total_centavos: int
    metodo_pago: PaymentMethod

    dian_status: DianStatus = Field(default=DianStatus.none)
    cufe: str | None = Field(default=None, max_length=255)
    wompi_transaction_id: str | None = Field(default=None, max_length=255)

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)
