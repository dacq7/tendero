"""DTOs de pago. Dinero en centavos. NUNCA exponen secretos ni la llave privada.

Endurecimiento Fase 6 B.1: tampoco viaja la llave PÚBLICA de Wompi. El Widget real
no está integrado y el cliente no la usa, así que se omite del DTO (minimización de
superficie). Cuando se integre el Widget, el frontend la pedirá a un endpoint propio.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.models.payment import PaymentProvider, PaymentStatus
from app.models.sale import PaymentMethod


class PaymentCreate(BaseModel):
    sale_id: int


class PaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sale_id: int
    provider: PaymentProvider
    metodo: PaymentMethod
    status: PaymentStatus
    monto_centavos: int
    moneda: str
    referencia: str
    wompi_transaction_id: str | None
    created_at: datetime
    updated_at: datetime


class SimulateRequest(BaseModel):
    """Solo en modo mock: cierra el ciclo del webhook en la demo."""

    result: Literal["approved", "declined"]
