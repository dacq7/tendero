"""Lógica de pagos Wompi. No conoce HTTP.

`start_payment` inicia la transacción (idempotente por venta). `process_webhook`
confirma de forma IDEMPOTENTE: el UNIQUE de webhook_events es el candado, y un
Payment en estado terminal es la defensa en profundidad. La venta NO se marca
pagada hasta que el webhook lo confirma.
"""

import hashlib
import json
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from app.models.inventory_movement import MovementType
from app.models.payment import (
    TERMINAL_PAYMENT_STATUSES,
    Payment,
    PaymentStatus,
)
from app.models.sale import SaleStatus
from app.models.user import User, UserRole
from app.models.webhook_event import WebhookEvent
from app.repositories import payment_repository, sale_repository
from app.services import inventory_service, product_service, sale_service
from app.services.payment_errors import (
    InvalidSignature,
    PaymentNotFound,
    SaleNotPayable,
    WebhookReplay,
)
from app.services.payments.factory import get_wompi_provider
from app.services.payments.provider import WebhookEnvelope

_MONEDA = "COP"

# Ventana de frescura del webhook (anti-replay). Un evento firmado pero más viejo
# que esto se rechaza aunque su firma sea válida; la idempotencia por event_id es la
# segunda capa. Se tolera un pequeño desfase de reloj hacia el futuro.
_WEBHOOK_MAX_AGE_S = 300  # 5 min
_WEBHOOK_FUTURE_SKEW_S = 60  # 1 min


def _reference_for(sale_id: int) -> str:
    return f"SALE-{sale_id:06d}"


def start_payment(session: Session, sale_id: int, *, actor: User) -> Payment:
    """Inicia (o recupera) el pago Wompi de una venta `pendiente_pago`."""
    sale = sale_service.get_sale(session, sale_id)
    if actor.role != UserRole.admin and sale.user_id != actor.id:
        raise SaleNotPayable("No puedes pagar una venta que no es tuya")
    if sale.status != SaleStatus.pendiente_pago:
        raise SaleNotPayable(f"La venta {sale_id} no admite pago (estado: {sale.status.value})")

    # Idempotencia: si ya existe un pago para la venta, devolverlo (no duplicar
    # la transacción Wompi). Cubre reintentos del frontend.
    existing = payment_repository.get_by_sale(session, sale_id)
    if existing is not None:
        return existing

    provider = get_wompi_provider()
    referencia = _reference_for(sale_id)
    firma = provider.compute_integrity_signature(
        referencia=referencia, monto_centavos=sale.total_centavos, moneda=_MONEDA
    )
    result = provider.create_transaction(
        referencia=referencia,
        monto_centavos=sale.total_centavos,
        moneda=_MONEDA,
        metodo=sale.metodo_pago,
    )
    payment = Payment(
        sale_id=sale_id,
        provider=provider.name,
        metodo=sale.metodo_pago,
        status=result.status,
        monto_centavos=sale.total_centavos,
        moneda=_MONEDA,
        referencia=referencia,
        wompi_transaction_id=result.transaction_id,
        integrity_signature=firma,
    )
    payment_repository.add(session, payment)
    session.commit()
    session.refresh(payment)
    return payment


def get_payment(session: Session, payment_id: int, *, actor: User) -> Payment:
    payment = payment_repository.get(session, payment_id)
    if payment is None:
        raise PaymentNotFound(f"Pago {payment_id} no encontrado")
    sale = sale_repository.get(session, payment.sale_id)
    if actor.role != UserRole.admin and (sale is None or sale.user_id != actor.id):
        raise PaymentNotFound(f"Pago {payment_id} no encontrado")
    return payment


def get_payment_by_sale(session: Session, sale_id: int, *, actor: User) -> Payment:
    sale = sale_service.get_sale(session, sale_id)
    if actor.role != UserRole.admin and sale.user_id != actor.id:
        raise PaymentNotFound(f"La venta {sale_id} no tiene pago")
    payment = payment_repository.get_by_sale(session, sale_id)
    if payment is None:
        raise PaymentNotFound(f"La venta {sale_id} no tiene pago")
    return payment


def process_webhook(session: Session, payload: dict) -> None:
    """Procesa un evento Wompi de forma idempotente. Lanza InvalidSignature si la
    firma no valida (el router lo traduce a 400)."""
    provider = get_wompi_provider()
    envelope = provider.verify_and_parse_event(payload)  # valida firma

    # Anti-replay: un evento con firma válida pero fuera de la ventana de frescura se
    # rechaza (un atacante podría recapturar y reenviar un evento legítimo antiguo).
    # Va ANTES de registrar el evento para no consumir la clave de idempotencia.
    now = int(datetime.now(UTC).timestamp())
    age = now - envelope.timestamp
    if age > _WEBHOOK_MAX_AGE_S or age < -_WEBHOOK_FUTURE_SKEW_S:
        raise WebhookReplay("Evento fuera de la ventana de frescura")

    # Candado de idempotencia: registrar el evento ANTES de aplicar efectos. Si ya
    # existe (UNIQUE), es un reproceso → no-op.
    payload_hash = hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()
    # SAVEPOINT: aísla el intento de inserción. Si el evento ya existe (UNIQUE), se
    # revierte SOLO el savepoint (no la transacción entera) y termina idempotente.
    try:
        with session.begin_nested():
            session.add(
                WebhookEvent(
                    provider=provider.name,
                    event_id=envelope.event_id,
                    payload_hash=payload_hash,
                )
            )
    except IntegrityError:
        return  # evento ya procesado: no-op

    payment = payment_repository.get_by_wompi_tx_for_update(session, envelope.transaction_id)
    if payment is None or payment.status in TERMINAL_PAYMENT_STATUSES:
        # Pago desconocido o ya resuelto: deja el evento registrado y termina.
        session.commit()
        return

    # Defensa en profundidad: el evento DEBE corresponder al pago registrado
    # (monto y referencia), además de la firma ya validada.
    if (
        envelope.monto_centavos != payment.monto_centavos
        or envelope.referencia != payment.referencia
    ):
        raise InvalidSignature("El evento no corresponde al pago registrado")

    _apply_resolution(session, payment, envelope)
    session.commit()


def _apply_resolution(session: Session, payment: Payment, envelope: WebhookEnvelope) -> None:
    sale = sale_repository.get_for_update(session, payment.sale_id)

    if envelope.status == PaymentStatus.approved:
        payment.status = PaymentStatus.approved
        sale.status = SaleStatus.pagada
        sale.metodo_pago = payment.metodo
        sale.paid_at = datetime.now(UTC)
        sale_service.emit_invoice(
            session,
            sale,
            metodo_pago=payment.metodo,
            wompi_transaction_id=payment.wompi_transaction_id,
        )
    else:
        # declined / error / voided → venta rechazada + reverso de stock reservado.
        payment.status = envelope.status
        sale.status = SaleStatus.rechazada
        for item in sale_repository.items_for_sale(session, sale.id):
            product = product_service.get_locked(session, item.product_id)
            inventory_service.apply_movement(
                session,
                product,
                tipo=MovementType.reverso_venta,
                cantidad_milesimas=item.cantidad_milesimas,
                motivo="Reverso por pago rechazado",
                user_id=sale.user_id,
            )

    payment_repository.add(session, payment)
    sale_repository.add(session, sale)
