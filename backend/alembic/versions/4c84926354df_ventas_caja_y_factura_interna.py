"""ventas caja y factura interna

Revision ID: 4c84926354df
Revises: c025802323ed
Create Date: 2026-06-09 19:12:19.455829

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "4c84926354df"
down_revision: str | None = "c025802323ed"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Enums. `ivarate` YA existe (Fase 1): se referencia con create_type=False para
# no recrearlo. Los nuevos se crean una sola vez (checkfirst) antes de las tablas;
# las referencias en las columnas usan create_type=False para que create_table no
# intente recrearlos (paymentmethod se usa en sales E invoices).
cashsessionstatus = postgresql.ENUM(
    "abierta", "cerrada", name="cashsessionstatus", create_type=False
)
salestatus = postgresql.ENUM(
    "pendiente", "pagada", "anulada", name="salestatus", create_type=False
)
paymentmethod = postgresql.ENUM(
    "efectivo", "tarjeta", "nequi", "transferencia", name="paymentmethod", create_type=False
)
dianstatus = postgresql.ENUM(
    "none", "pending", "accepted", "rejected", name="dianstatus", create_type=False
)
ivarate = postgresql.ENUM(
    "exento", "tarifa_0", "tarifa_5", "tarifa_19", name="ivarate", create_type=False
)

_NUEVOS_ENUMS = (cashsessionstatus, salestatus, paymentmethod, dianstatus)


def upgrade() -> None:
    bind = op.get_bind()
    for enum in _NUEVOS_ENUMS:
        enum.create(bind, checkfirst=True)

    op.create_table(
        "invoice_sequences",
        sa.Column("serie", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column("last_numero", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("serie"),
    )
    # Seed de la serie POS: la fila debe existir para bloquearla (FOR UPDATE)
    # desde la primera venta.
    op.execute("INSERT INTO invoice_sequences (serie, last_numero) VALUES ('POS', 0)")

    op.create_table(
        "cash_register_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("status", cashsessionstatus, nullable=False),
        sa.Column("monto_inicial_centavos", sa.Integer(), nullable=False),
        sa.Column("abierta_at", sa.DateTime(), nullable=False),
        sa.Column("cerrada_at", sa.DateTime(), nullable=True),
        sa.Column("closed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("efectivo_contado_centavos", sa.Integer(), nullable=True),
        sa.Column("efectivo_esperado_centavos", sa.Integer(), nullable=True),
        sa.Column("diferencia_centavos", sa.Integer(), nullable=True),
        sa.Column("nota_cierre", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.CheckConstraint("monto_inicial_centavos >= 0", name="ck_cash_monto_inicial_no_neg"),
        sa.ForeignKeyConstraint(["closed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_cash_register_sessions_status"), "cash_register_sessions", ["status"]
    )
    op.create_index(
        op.f("ix_cash_register_sessions_user_id"), "cash_register_sessions", ["user_id"]
    )

    op.create_table(
        "sales",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cash_session_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("customer_doc", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=True),
        sa.Column(
            "customer_nombre", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True
        ),
        sa.Column("subtotal_centavos", sa.Integer(), nullable=False),
        sa.Column("iva_total_centavos", sa.Integer(), nullable=False),
        sa.Column("total_centavos", sa.Integer(), nullable=False),
        sa.Column("status", salestatus, nullable=False),
        sa.Column("metodo_pago", paymentmethod, nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("paid_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint("iva_total_centavos >= 0", name="ck_sales_iva_no_neg"),
        sa.CheckConstraint("subtotal_centavos >= 0", name="ck_sales_subtotal_no_neg"),
        sa.CheckConstraint(
            "total_centavos = subtotal_centavos + iva_total_centavos",
            name="ck_sales_total_coherente",
        ),
        sa.CheckConstraint("total_centavos >= 0", name="ck_sales_total_no_neg"),
        sa.ForeignKeyConstraint(
            ["cash_session_id"], ["cash_register_sessions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sales_cash_session_id"), "sales", ["cash_session_id"])
    op.create_index(op.f("ix_sales_status"), "sales", ["status"])
    op.create_index(op.f("ix_sales_user_id"), "sales", ["user_id"])

    op.create_table(
        "invoices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sale_id", sa.Integer(), nullable=False),
        sa.Column("serie", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column("numero", sa.Integer(), nullable=False),
        sa.Column("numero_completo", sqlmodel.sql.sqltypes.AutoString(length=40), nullable=False),
        sa.Column("subtotal_centavos", sa.Integer(), nullable=False),
        sa.Column("iva_total_centavos", sa.Integer(), nullable=False),
        sa.Column("total_centavos", sa.Integer(), nullable=False),
        sa.Column("metodo_pago", paymentmethod, nullable=False),
        sa.Column("dian_status", dianstatus, nullable=False),
        sa.Column("cufe", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
        sa.Column(
            "wompi_transaction_id", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("iva_total_centavos >= 0", name="ck_invoices_iva_no_neg"),
        sa.CheckConstraint("subtotal_centavos >= 0", name="ck_invoices_subtotal_no_neg"),
        sa.CheckConstraint("total_centavos >= 0", name="ck_invoices_total_no_neg"),
        sa.ForeignKeyConstraint(["sale_id"], ["sales.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("numero_completo", name="uq_invoices_numero_completo"),
        sa.UniqueConstraint("sale_id", name="uq_invoices_sale"),
        sa.UniqueConstraint("serie", "numero", name="uq_invoices_serie_numero"),
    )
    op.create_index(op.f("ix_invoices_numero_completo"), "invoices", ["numero_completo"])
    op.create_index(op.f("ix_invoices_sale_id"), "invoices", ["sale_id"])

    op.create_table(
        "sale_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sale_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("nombre_snapshot", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column("sku_snapshot", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column("cantidad_milesimas", sa.Integer(), nullable=False),
        sa.Column("precio_unitario_centavos", sa.Integer(), nullable=False),
        sa.Column("iva_rate_snapshot", ivarate, nullable=False),
        sa.Column("iva_bps_snapshot", sa.Integer(), nullable=False),
        sa.Column("base_centavos", sa.Integer(), nullable=False),
        sa.Column("iva_centavos", sa.Integer(), nullable=False),
        sa.Column("total_linea_centavos", sa.Integer(), nullable=False),
        sa.CheckConstraint("base_centavos >= 0", name="ck_sale_items_base_no_neg"),
        sa.CheckConstraint("cantidad_milesimas > 0", name="ck_sale_items_cantidad_pos"),
        sa.CheckConstraint("iva_centavos >= 0", name="ck_sale_items_iva_no_neg"),
        sa.CheckConstraint("precio_unitario_centavos >= 0", name="ck_sale_items_precio_no_neg"),
        sa.CheckConstraint("total_linea_centavos >= 0", name="ck_sale_items_total_no_neg"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["sale_id"], ["sales.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sale_items_product_id"), "sale_items", ["product_id"])
    op.create_index(op.f("ix_sale_items_sale_id"), "sale_items", ["sale_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_sale_items_sale_id"), table_name="sale_items")
    op.drop_index(op.f("ix_sale_items_product_id"), table_name="sale_items")
    op.drop_table("sale_items")
    op.drop_index(op.f("ix_invoices_sale_id"), table_name="invoices")
    op.drop_index(op.f("ix_invoices_numero_completo"), table_name="invoices")
    op.drop_table("invoices")
    op.drop_index(op.f("ix_sales_user_id"), table_name="sales")
    op.drop_index(op.f("ix_sales_status"), table_name="sales")
    op.drop_index(op.f("ix_sales_cash_session_id"), table_name="sales")
    op.drop_table("sales")
    op.drop_index(op.f("ix_cash_register_sessions_user_id"), table_name="cash_register_sessions")
    op.drop_index(op.f("ix_cash_register_sessions_status"), table_name="cash_register_sessions")
    op.drop_table("cash_register_sessions")
    op.drop_table("invoice_sequences")
    # Eliminar solo los enums NUEVOS de esta fase (ivarate es de Fase 1).
    for enum_name in ("dianstatus", "salestatus", "paymentmethod", "cashsessionstatus"):
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
