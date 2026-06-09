"""Modelo de producto del catálogo.

Convenciones de dominio (CLAUDE.md):
- Dinero en ENTEROS de centavos COP (`*_centavos`). Nunca float.
- Cantidades/stock en ENTEROS de milésimas de la unidad (`*_milesimas`):
  1000 = 1 unidad / 1 kg. Cubre granel hasta el gramo con aritmética exacta.
"""

from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint
from sqlmodel import Field, SQLModel


class ProductUnit(StrEnum):
    unidad = "unidad"
    kg = "kg"
    g = "g"
    litro = "litro"
    ml = "ml"
    paquete = "paquete"


class IvaRate(StrEnum):
    """Tarifas de IVA de Colombia. `exento` (no causa IVA) ≠ `tarifa_0`
    (gravado a tarifa cero): distinción fiscal real para la DIAN (Fase 4)."""

    exento = "exento"
    tarifa_0 = "tarifa_0"
    tarifa_5 = "tarifa_5"
    tarifa_19 = "tarifa_19"


# Mapeo tarifa → puntos básicos (en código, no en DB). Para cálculos de IVA.
IVA_RATE_BPS: dict[IvaRate, int] = {
    IvaRate.exento: 0,
    IvaRate.tarifa_0: 0,
    IvaRate.tarifa_5: 500,
    IvaRate.tarifa_19: 1900,
}


class Product(SQLModel, table=True):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("precio_costo_centavos >= 0", name="ck_products_precio_costo_no_neg"),
        CheckConstraint("precio_venta_centavos >= 0", name="ck_products_precio_venta_no_neg"),
        CheckConstraint("stock_milesimas >= 0", name="ck_products_stock_no_neg"),
        CheckConstraint("stock_minimo_milesimas >= 0", name="ck_products_stock_min_no_neg"),
    )

    id: int | None = Field(default=None, primary_key=True)
    nombre: str = Field(index=True, max_length=255)
    sku: str = Field(unique=True, index=True, max_length=64)
    # Postgres permite múltiples NULL en una columna UNIQUE: varios productos sin
    # código de barras conviven, pero un código presente debe ser único.
    codigo_barras: str | None = Field(default=None, unique=True, index=True, max_length=64)
    categoria: str | None = Field(default=None, index=True, max_length=120)
    supplier_id: int | None = Field(default=None, foreign_key="suppliers.id", ondelete="SET NULL")

    precio_costo_centavos: int = Field(default=0)
    precio_venta_centavos: int = Field(default=0)
    iva: IvaRate = Field(default=IvaRate.tarifa_19)
    unidad: ProductUnit = Field(default=ProductUnit.unidad)

    stock_milesimas: int = Field(default=0)
    stock_minimo_milesimas: int = Field(default=0)
    activo: bool = Field(default=True)

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        nullable=False,
        sa_column_kwargs={"onupdate": lambda: datetime.now(UTC)},
    )
