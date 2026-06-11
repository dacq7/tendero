"""Interfaz `WompiProvider` (adaptador) + DTOs + parseo/verificación de eventos.

El parseo y verificación del webhook es idéntico para mock y real (mismo formato
de evento Wompi), así que vive aquí y ambas implementaciones lo reutilizan.
"""

import hmac
import time
from dataclasses import dataclass
from typing import Protocol

from app.models.payment import PaymentMethod, PaymentProvider, PaymentStatus
from app.services.payment_errors import InvalidSignature
from app.services.payments.signing import _dotted, event_checksum

# Estado Wompi (string del API) → nuestro PaymentStatus.
WOMPI_STATUS_MAP: dict[str, PaymentStatus] = {
    "PENDING": PaymentStatus.pending,
    "APPROVED": PaymentStatus.approved,
    "DECLINED": PaymentStatus.declined,
    "VOIDED": PaymentStatus.voided,
    "ERROR": PaymentStatus.error,
}


@dataclass(frozen=True)
class TransactionResult:
    transaction_id: str
    status: PaymentStatus
    referencia: str
    monto_centavos: int


@dataclass(frozen=True)
class WebhookEnvelope:
    event_id: str  # clave de idempotencia (transaction_id + status)
    transaction_id: str
    status: PaymentStatus
    referencia: str
    monto_centavos: int
    timestamp: int  # epoch s del evento (firmado); usado para rechazar replays viejos


class WompiProvider(Protocol):
    name: PaymentProvider

    def compute_integrity_signature(
        self, *, referencia: str, monto_centavos: int, moneda: str
    ) -> str: ...

    def create_transaction(
        self, *, referencia: str, monto_centavos: int, moneda: str, metodo: PaymentMethod
    ) -> TransactionResult: ...

    def get_transaction(self, transaction_id: str) -> TransactionResult: ...

    def verify_and_parse_event(self, payload: dict) -> WebhookEnvelope: ...


_SIGNED_PROPERTIES = ["transaction.id", "transaction.status", "transaction.amount_in_cents"]


def build_signed_event(
    *,
    transaction_id: str,
    status: str,  # string Wompi: APPROVED, DECLINED, ...
    referencia: str,
    monto_centavos: int,
    events_secret: str,
    timestamp: int | str | None = None,
) -> dict:
    """Construye un evento Wompi con checksum VÁLIDO (para mock/simulate y tests).

    Pasa por el mismo `verify_and_parse_event`, así que ejercita la firma real.
    Por defecto usa el timestamp ACTUAL (epoch s): así los eventos del mock/simulate
    pasan la verificación de frescura del webhook. Los tests pueden inyectar un
    timestamp viejo/futuro explícito para ejercitar la protección de replay.
    """
    if timestamp is None:
        timestamp = int(time.time())
    tx = {
        "id": transaction_id,
        "status": status,
        "reference": referencia,
        "amount_in_cents": monto_centavos,
    }
    values = [str(transaction_id), str(status), str(monto_centavos)]
    checksum = event_checksum(values, timestamp, events_secret)
    return {
        "event": "transaction.updated",
        "data": {"transaction": tx},
        "timestamp": timestamp,
        "signature": {"properties": _SIGNED_PROPERTIES, "checksum": checksum},
    }


def verify_and_parse_event(payload: dict, *, events_secret: str) -> WebhookEnvelope:
    """Valida el checksum del evento Wompi y devuelve el sobre normalizado.

    Lanza InvalidSignature si el checksum no coincide (o el payload es inválido).
    """
    # Mensaje genérico para TODOS los fallos de firma: no revelar a un cliente
    # no autenticado la causa interna ni valores recibidos.
    generico = "Firma de evento inválida"
    try:
        signature = payload["signature"]
        properties: list[str] = signature["properties"]
        checksum: str = signature["checksum"]
        timestamp = payload["timestamp"]
        tx = payload["data"]["transaction"]
        status_str = tx["status"]
    except (KeyError, TypeError) as exc:
        raise InvalidSignature(generico) from exc

    # Solo se aceptan exactamente las propiedades firmadas conocidas: evita que un
    # payload controlado por el atacante haga traversar rutas arbitrarias.
    if set(properties) != set(_SIGNED_PROPERTIES):
        raise InvalidSignature(generico)

    values = [str(_dotted(payload, f"data.{p}")) for p in properties]
    expected = event_checksum(values, timestamp, events_secret)
    # Comparación de tiempo constante (anti timing-attack).
    if not hmac.compare_digest(expected, str(checksum)):
        raise InvalidSignature(generico)

    status = WOMPI_STATUS_MAP.get(status_str)
    if status is None:
        raise InvalidSignature(generico)

    # El timestamp ya está cubierto por el checksum (no es manipulable sin romper la
    # firma); aquí solo se normaliza a int para la verificación de frescura aguas
    # abajo. Si no es numérico, se trata como firma inválida.
    try:
        ts = int(timestamp)
    except (TypeError, ValueError) as exc:
        raise InvalidSignature(generico) from exc

    transaction_id = str(tx["id"])
    return WebhookEnvelope(
        event_id=f"{transaction_id}:{status.value}",
        transaction_id=transaction_id,
        status=status,
        referencia=str(tx["reference"]),
        monto_centavos=int(tx["amount_in_cents"]),
        timestamp=ts,
    )
