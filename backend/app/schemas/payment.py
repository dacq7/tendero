"""DTOs de pago. Dinero en centavos. NUNCA exponen secretos ni la llave privada;
sí la llave PÚBLICA (para el Widget de Wompi en el cliente)."""

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
    # Llave pública para el Widget (no es secreto). La privada nunca sale del server.
    wompi_public_key: str | None = None


class SimulateRequest(BaseModel):
    """Solo en modo mock: cierra el ciclo del webhook en la demo."""

    result: Literal["approved", "declined"]
