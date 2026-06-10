"""fase4 facturacion dian resolucion y emision fiscal

Revision ID: 68585982b58f
Revises: 9a1dd4b41864
Create Date: 2026-06-10 01:49:41.043951

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "68585982b58f"
down_revision: str | None = "9a1dd4b41864"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Enum NUEVO de esta fase (se crea una vez, checkfirst).
fiscalprovider = postgresql.ENUM("mock", "pt", name="fiscalprovider", create_type=False)
# Enum EXISTENTE (Fase 3): reutilizado sin recrear.
dianstatus = postgresql.ENUM(
    "none", "pending", "accepted", "rejected", name="dianstatus", create_type=False
)


def upgrade() -> None:
    fiscalprovider.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "invoice_resolutions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("numero_resolucion", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column("prefijo", sqlmodel.sql.sqltypes.AutoString(length=10), nullable=False),
        sa.Column("numero_desde", sa.Integer(), nullable=False),
        sa.Column("numero_hasta", sa.Integer(), nullable=False),
        sa.Column("last_numero", sa.Integer(), nullable=False),
        sa.Column("vigencia_desde", sa.Date(), nullable=False),
        sa.Column("vigencia_hasta", sa.Date(), nullable=False),
        sa.Column("rut_nit", sqlmodel.sql.sqltypes.AutoString(length=32), nullable=False),
        sa.Column("responsabilidad", sqlmodel.sql.sqltypes.AutoString(length=8), nullable=False),
        sa.Column("activa", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("last_numero >= numero_desde - 1", name="ck_resolution_last"),
        sa.CheckConstraint("numero_hasta >= numero_desde", name="ck_resolution_rango"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_resolution_activa",
        "invoice_resolutions",
        ["activa"],
        unique=True,
        postgresql_where=sa.text("activa"),
    )
    # Resolución de DEMO (mock): permite emitir sin configurar nada. SIN validez
    # fiscal. SOLO DEMO: reemplazar NIT, número de resolución, prefijo y rango por
    # los reales del comercio antes de cualquier uso en producción.
    op.execute(
        """
        INSERT INTO invoice_resolutions
          (numero_resolucion, prefijo, numero_desde, numero_hasta, last_numero,
           vigencia_desde, vigencia_hasta, rut_nit, responsabilidad, activa, created_at)
        VALUES
          ('DEMO-18764', 'SETP', 990000001, 995000000, 990000000,
           '2020-01-01', '2035-12-31', '900000000-0', '52', true, now())
        """
    )

    op.create_table(
        "fiscal_emissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("invoice_id", sa.Integer(), nullable=False),
        sa.Column("resolution_id", sa.Integer(), nullable=False),
        sa.Column("prefijo", sqlmodel.sql.sqltypes.AutoString(length=10), nullable=False),
        sa.Column("numero_fiscal", sa.Integer(), nullable=False),
        sa.Column(
            "numero_fiscal_completo", sqlmodel.sql.sqltypes.AutoString(length=40), nullable=False
        ),
        sa.Column("provider", fiscalprovider, nullable=False),
        sa.Column("status", dianstatus, nullable=False),
        sa.Column("cufe", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
        sa.Column("pt_document_id", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
        sa.Column("motivo_rechazo", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.Column("intentos", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["resolution_id"], ["invoice_resolutions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invoice_id", name="uq_fiscal_emissions_invoice"),
        sa.UniqueConstraint("numero_fiscal_completo", name="uq_fiscal_emissions_numero"),
        sa.UniqueConstraint(
            "resolution_id", "numero_fiscal", name="uq_fiscal_emissions_res_numero"
        ),
    )
    op.create_index(op.f("ix_fiscal_emissions_invoice_id"), "fiscal_emissions", ["invoice_id"])
    op.create_index(
        op.f("ix_fiscal_emissions_resolution_id"), "fiscal_emissions", ["resolution_id"]
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_fiscal_emissions_resolution_id"), table_name="fiscal_emissions")
    op.drop_index(op.f("ix_fiscal_emissions_invoice_id"), table_name="fiscal_emissions")
    op.drop_table("fiscal_emissions")
    op.drop_index(
        "uq_resolution_activa",
        table_name="invoice_resolutions",
        postgresql_where=sa.text("activa"),
    )
    op.drop_table("invoice_resolutions")
    # Solo el enum NUEVO de esta fase (dianstatus es de Fase 3).
    op.execute("DROP TYPE IF EXISTS fiscalprovider")
