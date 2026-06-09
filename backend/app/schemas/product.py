"""DTOs de producto. Dinero en centavos, cantidades en milésimas (enteros).

`ProductRead` expone margen calculado (centavos y %) desde una única fuente:
app.services.costing. El stock NUNCA se fija por estos DTOs; cambia solo vía
movimientos de inventario (kardex).
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.models.product import IvaRate, ProductUnit
from app.services import costing


class ProductCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=255)
    sku: str = Field(min_length=1, max_length=64)
    codigo_barras: str | None = None
    categoria: str | None = None
    supplier_id: int | None = None
    precio_costo_centavos: int = Field(default=0, ge=0)
    precio_venta_centavos: int = Field(default=0, ge=0)
    iva: IvaRate = IvaRate.tarifa_19
    unidad: ProductUnit = ProductUnit.unidad
    stock_minimo_milesimas: int = Field(default=0, ge=0)


class ProductUpdate(BaseModel):
    nombre: str | None = None
    sku: str | None = None
    codigo_barras: str | None = None
    categoria: str | None = None
    supplier_id: int | None = None
    precio_costo_centavos: int | None = Field(default=None, ge=0)
    precio_venta_centavos: int | None = Field(default=None, ge=0)
    iva: IvaRate | None = None
    unidad: ProductUnit | None = None
    stock_minimo_milesimas: int | None = Field(default=None, ge=0)
    activo: bool | None = None


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    sku: str
    codigo_barras: str | None
    categoria: str | None
    supplier_id: int | None
    precio_costo_centavos: int
    precio_venta_centavos: int
    iva: IvaRate
    unidad: ProductUnit
    stock_milesimas: int
    stock_minimo_milesimas: int
    activo: bool
    created_at: datetime
    updated_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def margen_centavos(self) -> int:
        return costing.margin_centavos(self.precio_venta_centavos, self.precio_costo_centavos)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def margen_bps(self) -> int | None:
        return costing.margin_bps(self.precio_venta_centavos, self.precio_costo_centavos)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def stock_bajo(self) -> bool:
        # Mínimo en 0 = sin control de mínimo: no se considera stock bajo.
        return (
            self.stock_minimo_milesimas > 0 and self.stock_milesimas <= self.stock_minimo_milesimas
        )
