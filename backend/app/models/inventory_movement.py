"""Kardex: registro auditable de cada movimiento de inventario.

`apply_movement` (inventory_service) es el ÚNICO camino que crea estos registros
y actualiza `product.stock_milesimas`. `cantidad_milesimas` es SIEMPRE positiva;
el signo lo determina el `tipo`. `stock_resultante_milesimas` es un snapshot del
stock tras aplicar el movimiento (permite auditar/reparar divergencias).
"""

from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint
from sqlmodel import Field, Index, SQLModel


class MovementType(StrEnum):
    entrada = "entrada"  # +stock (compra/ingreso)
    salida = "salida"  # -stock (venta/egreso)
    ajuste = "ajuste"  # fija el stock a un valor objetivo (delta firmado)
    merma = "merma"  # -stock (daño/vencimiento/pérdida)
    reverso_venta = "reverso_venta"  # +stock por venta rechazada (NO recostea)


class InventoryMovement(SQLModel, table=True):
    __tablename__ = "inventory_movements"
    __table_args__ = (
        CheckConstraint("cantidad_milesimas > 0", name="ck_movements_cantidad_pos"),
        CheckConstraint(
            "costo_unitario_centavos IS NULL OR costo_unitario_centavos >= 0",
            name="ck_movements_costo_no_neg",
        ),
        Index("ix_movements_product_created", "product_id", "created_at"),
    )

    id: int | None = Field(default=None, primary_key=True)
    product_id: int = Field(foreign_key="products.id", ondelete="RESTRICT", index=True)
    tipo: MovementType
    cantidad_milesimas: int
    costo_unitario_centavos: int | None = Field(default=None)
    stock_resultante_milesimas: int
    motivo: str | None = Field(default=None, max_length=255)
    user_id: int | None = Field(default=None, foreign_key="users.id", ondelete="SET NULL")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), nullable=False, index=True
    )
