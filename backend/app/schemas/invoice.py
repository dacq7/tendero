"""DTOs de factura interna. Dinero en centavos."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.invoice import DianStatus
from app.models.sale import PaymentMethod


class InvoiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sale_id: int
    serie: str
    numero: int
    numero_completo: str
    subtotal_centavos: int
    iva_total_centavos: int
    total_centavos: int
    metodo_pago: PaymentMethod
    dian_status: DianStatus
    cufe: str | None = None
    created_at: datetime
