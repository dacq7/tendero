"""fase3 payments webhook_events estados wompi

Revision ID: 9a1dd4b41864
Revises: 4c84926354df
Create Date: 2026-06-10 01:01:41.699238

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "9a1dd4b41864"
down_revision: str | None = "4c84926354df"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Enums NUEVOS de esta fase (se crean una vez, checkfirst).
paymentprovider = postgresql.ENUM("mock", "wompi", name="paymentprovider", create_type=False)
paymentstatus = postgresql.ENUM(
    "pending", "approved", "declined", "error", "voided", name="paymentstatus", create_type=False
)
# Enum EXISTENTE (Fase 2) reutilizado: NO recrear (ya incluirá 'pse' tras el ADD VALUE).
paymentmethod = postgresql.ENUM(
    "efectivo", "transferencia", "tarjeta", "pse", "nequi", name="paymentmethod", create_type=False
)

# Valores nuevos para enums existentes. ALTER TYPE ... ADD VALUE no lo genera el
# autogenerate; en Postgres 16 corre dentro de la transacción (no se usan los
# valores como dato en esta misma migración).
_ADD_VALUES = [
    ("salestatus", "pendiente_pago"),
    ("salestatus", "rechazada"),
    ("paymentmethod", "pse"),
    ("movementtype", "reverso_venta"),
]


def upgrade() -> None:
    for enum_name, value in _ADD_VALUES:
        op.execute(f"ALTER TYPE {enum_name} ADD VALUE IF NOT EXISTS '{value}'")

    bind = op.get_bind()
    paymentprovider.create(bind, checkfirst=True)
    paymentstatus.create(bind, checkfirst=True)

    op.create_table(
        "webhook_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("provider", paymentprovider, nullable=False),
        sa.Column("event_id", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column("payload_hash", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column("processed_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "event_id", name="uq_webhook_provider_event"),
    )
    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sale_id", sa.Integer(), nullable=False),
        sa.Column("provider", paymentprovider, nullable=False),
        sa.Column("metodo", paymentmethod, nullable=False),
        sa.Column("status", paymentstatus, nullable=False),
        sa.Column("monto_centavos", sa.Integer(), nullable=False),
        sa.Column("moneda", sqlmodel.sql.sqltypes.AutoString(length=3), nullable=False),
        sa.Column("referencia", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column(
            "wompi_transaction_id", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True
        ),
        sa.Column(
            "integrity_signature", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("monto_centavos > 0", name="ck_payments_monto_pos"),
        sa.ForeignKeyConstraint(["sale_id"], ["sales.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("referencia", name="uq_payments_referencia"),
        sa.UniqueConstraint("sale_id", name="uq_payments_sale"),
    )
    op.create_index(op.f("ix_payments_sale_id"), "payments", ["sale_id"])
    op.create_index(op.f("ix_payments_status"), "payments", ["status"])
    op.create_index(
        op.f("ix_payments_wompi_transaction_id"), "payments", ["wompi_transaction_id"]
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_payments_wompi_transaction_id"), table_name="payments")
    op.drop_index(op.f("ix_payments_status"), table_name="payments")
    op.drop_index(op.f("ix_payments_sale_id"), table_name="payments")
    op.drop_table("payments")
    op.drop_table("webhook_events")
    # Solo los enums NUEVOS de esta fase. Los ADD VALUE en enums existentes
    # (salestatus/paymentmethod/movementtype) NO son reversibles sin recrear el
    # tipo: caso de borde aceptado (igual que la deuda 'userrole' anotada).
    for enum_name in ("paymentstatus", "paymentprovider"):
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
