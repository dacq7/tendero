"""RealWompiProvider: mapea al API real de Wompi (sandbox/prod).

Bien diseñado pero NO se ejecuta sin credenciales reales (proyecto de portafolio):
si falta la llave privada, falla ruidosamente con ProviderUnavailable. La llave
privada vive SOLO en el servidor; al cliente solo va la pública (Widget).
"""

import httpx

from app.core.config import settings
from app.models.payment import PaymentMethod, PaymentProvider, PaymentStatus
from app.services.payment_errors import ProviderUnavailable
from app.services.payments import provider as provider_mod
from app.services.payments.provider import (
    WOMPI_STATUS_MAP,
    TransactionResult,
    WebhookEnvelope,
)
from app.services.payments.signing import integrity_signature

# Sandbox de Wompi. En prod cambiaría por env var; fuera del alcance de esta fase.
_API_BASE = "https://sandbox.wompi.co/v1"
_TIMEOUT = 15.0


class RealWompiProvider:
    name = PaymentProvider.wompi

    def _require_key(self) -> str:
        if not settings.wompi_private_key:
            raise ProviderUnavailable(
                "WOMPI_PRIVATE_KEY no configurada: el proveedor real no puede operar. "
                "Usa WOMPI_PROVIDER=mock para la demo."
            )
        return settings.wompi_private_key

    def compute_integrity_signature(
        self, *, referencia: str, monto_centavos: int, moneda: str
    ) -> str:
        return integrity_signature(
            referencia, monto_centavos, moneda, settings.wompi_integrity_secret
        )

    def create_transaction(
        self, *, referencia: str, monto_centavos: int, moneda: str, metodo: PaymentMethod
    ) -> TransactionResult:
        private_key = self._require_key()
        firma = self.compute_integrity_signature(
            referencia=referencia, monto_centavos=monto_centavos, moneda=moneda
        )
        # Con Widget/Web Checkout, el token de tarjeta / datos de PSE/Nequi los
        # aporta el cliente; aquí se enviarían en `payment_method`. El mapeo exacto
        # depende del método y se completaría con credenciales reales.
        body = {
            "amount_in_cents": monto_centavos,
            "currency": moneda,
            "reference": referencia,
            "signature": firma,
            "payment_method": {"type": _wompi_method(metodo)},
        }
        resp = httpx.post(
            f"{_API_BASE}/transactions",
            json=body,
            headers={"Authorization": f"Bearer {private_key}"},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        tx = resp.json()["data"]
        return TransactionResult(
            transaction_id=str(tx["id"]),
            status=WOMPI_STATUS_MAP.get(tx["status"], PaymentStatus.pending),
            referencia=referencia,
            monto_centavos=monto_centavos,
        )

    def get_transaction(self, transaction_id: str) -> TransactionResult:
        private_key = self._require_key()
        resp = httpx.get(
            f"{_API_BASE}/transactions/{transaction_id}",
            headers={"Authorization": f"Bearer {private_key}"},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        tx = resp.json()["data"]
        return TransactionResult(
            transaction_id=str(tx["id"]),
            status=WOMPI_STATUS_MAP.get(tx["status"], PaymentStatus.pending),
            referencia=str(tx.get("reference", "")),
            monto_centavos=int(tx.get("amount_in_cents", 0)),
        )

    def verify_and_parse_event(self, payload: dict) -> WebhookEnvelope:
        return provider_mod.verify_and_parse_event(
            payload, events_secret=settings.wompi_events_secret
        )


def _wompi_method(metodo: PaymentMethod) -> str:
    return {
        PaymentMethod.tarjeta: "CARD",
        PaymentMethod.pse: "PSE",
        PaymentMethod.nequi: "NEQUI",
    }.get(metodo, "CARD")
