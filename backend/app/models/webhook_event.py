"""Registro de eventos de webhook procesados: candado de IDEMPOTENCIA.

El UNIQUE(provider, event_id) es la garantía dura: insertar el mismo evento dos
veces viola el constraint, así que reprocesar es un no-op aunque lleguen webhooks
concurrentes o reintentos del proveedor.
"""

from datetime import UTC, datetime

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel

from app.models.payment import PaymentProvider


class WebhookEvent(SQLModel, table=True):
    __tablename__ = "webhook_events"
    __table_args__ = (UniqueConstraint("provider", "event_id", name="uq_webhook_provider_event"),)

    id: int | None = Field(default=None, primary_key=True)
    provider: PaymentProvider
    event_id: str = Field(max_length=255)
    payload_hash: str = Field(max_length=64)
    processed_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)
