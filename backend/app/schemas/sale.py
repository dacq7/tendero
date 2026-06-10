"""DTOs de venta. El cliente NUNCA envía precios: solo product_id + cantidad y
método de pago. El servidor congela precio e IVA desde el producto.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.product import IvaRate
from app.models.sale import PaymentMethod, SaleStatus
from app.schemas.invoice import InvoiceRead


class SaleLineCreate(BaseModel):
    product_id: int
    cantidad_milesimas: int = Field(gt=0)


class SaleCreate(BaseModel):
    lineas: list[SaleLineCreate] = Field(min_length=1)
    metodo_pago: PaymentMethod
    customer_doc: str | None = Field(default=None, max_length=50)
    customer_nombre: str | None = Field(default=None, max_length=255)


class SaleItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    nombre_snapshot: str
    sku_snapshot: str
    cantidad_milesimas: int
    precio_unitario_centavos: int
    iva_rate_snapshot: IvaRate
    iva_bps_snapshot: int
    base_centavos: int
    iva_centavos: int
    total_linea_centavos: int


class SaleRead(BaseModel):
    """Detalle completo de la venta (incluye ítems y factura). El customer_doc
    se expone solo en el detalle (minimización Habeas Data)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    cash_session_id: int
    user_id: int
    customer_doc: str | None
    customer_nombre: str | None
    subtotal_centavos: int
    iva_total_centavos: int
    total_centavos: int
    status: SaleStatus
    metodo_pago: PaymentMethod | None
    created_at: datetime
    paid_at: datetime | None
    items: list[SaleItemRead]
    # None mientras el pago Wompi no se confirma (venta pendiente_pago/rechazada).
    invoice: InvoiceRead | None


class SaleSummary(BaseModel):
    """Vista de listado: sin ítems ni datos del cliente (Habeas Data)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    cash_session_id: int
    user_id: int
    subtotal_centavos: int
    iva_total_centavos: int
    total_centavos: int
    status: SaleStatus
    metodo_pago: PaymentMethod | None
    created_at: datetime
