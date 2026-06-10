"""MockWompiProvider: camino de demostración del portafolio.

Simula el flujo COMPLETO de Wompi sin llaves reales, pero con firmas SHA256
REALES (contra los secretos de prueba en .env): el webhook valida firma de
verdad y el ciclo pending → approved/declined se ejercita de punta a punta.
"""

import uuid

from app.core.config import settings
from app.models.payment import PaymentMethod, PaymentProvider, PaymentStatus
from app.services.payments import provider as provider_mod
from app.services.payments.provider import TransactionResult, WebhookEnvelope
from app.services.payments.signing import integrity_signature


class MockWompiProvider:
    name = PaymentProvider.mock

    def compute_integrity_signature(
        self, *, referencia: str, monto_centavos: int, moneda: str
    ) -> str:
        return integrity_signature(
            referencia, monto_centavos, moneda, settings.wompi_integrity_secret
        )

    def create_transaction(
        self, *, referencia: str, monto_centavos: int, moneda: str, metodo: PaymentMethod
    ) -> TransactionResult:
        # Transacción simulada: nace PENDING; el webhook (o /simulate) la resuelve.
        return TransactionResult(
            transaction_id=f"mock-tx-{uuid.uuid4().hex[:16]}",
            status=PaymentStatus.pending,
            referencia=referencia,
            monto_centavos=monto_centavos,
        )

    def get_transaction(self, transaction_id: str) -> TransactionResult:
        # El mock no guarda estado propio: la verdad vive en nuestra tabla payments.
        return TransactionResult(
            transaction_id=transaction_id,
            status=PaymentStatus.pending,
            referencia="",
            monto_centavos=0,
        )

    def verify_and_parse_event(self, payload: dict) -> WebhookEnvelope:
        return provider_mod.verify_and_parse_event(
            payload, events_secret=settings.wompi_events_secret
        )

    def build_event(self, *, transaction_id, status, referencia, monto_centavos) -> dict:
        """Para /payments/{id}/simulate: arma un evento firmado válido."""
        return provider_mod.build_signed_event(
            transaction_id=transaction_id,
            status=status,
            referencia=referencia,
            monto_centavos=monto_centavos,
            events_secret=settings.wompi_events_secret,
        )
