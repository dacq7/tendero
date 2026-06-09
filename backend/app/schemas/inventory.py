"""DTOs del kardex: movimientos, entradas de mercancía y alertas de stock.

Cantidades en milésimas (1000 = 1 unidad), dinero en centavos. Enteros siempre.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.models.inventory_movement import MovementType


class MovementCreate(BaseModel):
    product_id: int
    tipo: MovementType
    # entrada/salida/merma: magnitud del movimiento.
    # ajuste: stock objetivo (>0). Para dejar el stock en 0, usar salida/merma.
    cantidad_milesimas: int = Field(gt=0)
    costo_unitario_centavos: int | None = Field(default=None, ge=0)
    motivo: str | None = None


class MovementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    tipo: MovementType
    cantidad_milesimas: int
    costo_unitario_centavos: int | None
    stock_resultante_milesimas: int
    motivo: str | None
    user_id: int | None
    created_at: datetime


class GoodsEntryLine(BaseModel):
    product_id: int
    cantidad_milesimas: int = Field(gt=0)
    costo_unitario_centavos: int = Field(ge=0)


class GoodsEntryCreate(BaseModel):
    supplier_id: int | None = None
    motivo: str | None = None
    lineas: list[GoodsEntryLine] = Field(min_length=1)


class GoodsEntryRead(BaseModel):
    movimientos: list[MovementRead]


class LowStockAlert(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    sku: str
    unidad: str
    stock_milesimas: int
    stock_minimo_milesimas: int

    @computed_field  # type: ignore[prop-decorator]
    @property
    def faltante_milesimas(self) -> int:
        return max(0, self.stock_minimo_milesimas - self.stock_milesimas)
