"""Transacción de pago vinculada a una venta. Dinero en centavos COP.

El pago Wompi es asíncrono: nace `pending` y el webhook lo mueve a un estado
terminal (`approved`/`declined`/...). `referencia` es nuestra clave idempotente
hacia el proveedor (estable por venta): reintentar "iniciar pago" no duplica la
transacción.
"""

from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.models.sale import PaymentMethod


class PaymentStatus(StrEnum):
    pending = "pending"  # iniciada, esperando confirmación
    approved = "approved"  # aprobada (terminal)
    declined = "declined"  # rechazada (terminal)
    error = "error"  # error de proceso (terminal)
    voided = "voided"  # anulada (terminal)


class PaymentProvider(StrEnum):
    mock = "mock"
    wompi = "wompi"


# Estados terminales: un Payment en estos no se vuelve a mover (idempotencia).
TERMINAL_PAYMENT_STATUSES = frozenset(
    {PaymentStatus.approved, PaymentStatus.declined, PaymentStatus.error, PaymentStatus.voided}
)


class Payment(SQLModel, table=True):
    __tablename__ = "payments"
    __table_args__ = (
        UniqueConstraint("sale_id", name="uq_payments_sale"),  # 1 pago por venta
        UniqueConstraint("referencia", name="uq_payments_referencia"),
        CheckConstraint("monto_centavos > 0", name="ck_payments_monto_pos"),
    )

    id: int | None = Field(default=None, primary_key=True)
    sale_id: int = Field(foreign_key="sales.id", ondelete="RESTRICT", index=True)
    provider: PaymentProvider
    metodo: PaymentMethod
    status: PaymentStatus = Field(default=PaymentStatus.pending, index=True)
    monto_centavos: int
    moneda: str = Field(default="COP", max_length=3)
    referencia: str = Field(max_length=64)
    wompi_transaction_id: str | None = Field(default=None, max_length=255, index=True)
    # Firma de integridad (SHA256, no reversible al secreto). Auditoría/Widget.
    # NUNCA se expone en PaymentRead (el DTO no la declara).
    integrity_signature: str | None = Field(default=None, max_length=255)

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        nullable=False,
        sa_column_kwargs={"onupdate": lambda: datetime.now(UTC)},
    )
