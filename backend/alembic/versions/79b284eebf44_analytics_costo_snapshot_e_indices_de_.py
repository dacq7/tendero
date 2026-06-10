"""analytics costo snapshot e indices de ventas

Revision ID: 79b284eebf44
Revises: 68585982b58f
Create Date: 2026-06-10 02:32:16.588394

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "79b284eebf44"
down_revision: str | None = "68585982b58f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Columna con server_default '0' temporal para cubrir filas existentes; luego
    # se rellena (backfill) y se quita el default (el modelo usa default en Python).
    op.add_column(
        "sale_items",
        sa.Column(
            "costo_unitario_snapshot_centavos",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    # Backfill: el costo histórico real es irrecuperable; se aproxima con el costo
    # actual del producto (cosmético en portafolio; el seed de demo usa el costo
    # correcto al sembrar). Las ventas sin producto quedan en 0.
    op.execute(
        """
        UPDATE sale_items si
        SET costo_unitario_snapshot_centavos = p.precio_costo_centavos
        FROM products p
        WHERE p.id = si.product_id
        """
    )
    op.alter_column("sale_items", "costo_unitario_snapshot_centavos", server_default=None)
    op.create_check_constraint(
        "ck_sale_items_costo_no_neg", "sale_items", "costo_unitario_snapshot_centavos >= 0"
    )

    # Índices para las agregaciones de analítica (eje temporal = paid_at de pagadas).
    op.create_index("ix_sales_paid_at", "sales", ["paid_at"])
    op.create_index(
        "ix_sales_pagada_paid_at",
        "sales",
        ["paid_at"],
        postgresql_where=sa.text("status = 'pagada'"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_sales_pagada_paid_at",
        table_name="sales",
        postgresql_where=sa.text("status = 'pagada'"),
    )
    op.drop_index("ix_sales_paid_at", table_name="sales")
    op.drop_constraint("ck_sale_items_costo_no_neg", "sale_items", type_="check")
    op.drop_column("sale_items", "costo_unitario_snapshot_centavos")
