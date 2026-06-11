"""Endpoints de pagos. Orquestan; la lógica vive en payment_service.

Permisos: cajero/admin inician y consultan el pago de SUS ventas. El endpoint
/simulate solo existe en modo mock (cierra el ciclo del webhook en la demo).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.core.deps import require_role
from app.db.session import get_session
from app.models.payment import PaymentProvider
from app.models.user import User, UserRole
from app.routers._errors import http_error
from app.schemas.payment import PaymentCreate, PaymentRead, SimulateRequest
from app.services import payment_service
from app.services.payment_errors import PaymentError
from app.services.payments.factory import get_wompi_provider, is_mock

router = APIRouter(prefix="/payments", tags=["payments"])

_staff = require_role(UserRole.admin, UserRole.cajero)


def _to_read(payment) -> PaymentRead:
    return PaymentRead.model_validate(payment)


@router.post("", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
def start_payment(
    body: PaymentCreate,
    current_user: User = Depends(_staff),
    session: Session = Depends(get_session),
) -> PaymentRead:
    try:
        payment = payment_service.start_payment(session, body.sale_id, actor=current_user)
    except PaymentError as exc:
        raise http_error(exc) from exc
    return _to_read(payment)


@router.get("/{payment_id}", response_model=PaymentRead)
def get_payment(
    payment_id: int,
    current_user: User = Depends(_staff),
    session: Session = Depends(get_session),
) -> PaymentRead:
    try:
        payment = payment_service.get_payment(session, payment_id, actor=current_user)
    except PaymentError as exc:
        raise http_error(exc) from exc
    return _to_read(payment)


@router.get("/by-sale/{sale_id}", response_model=PaymentRead)
def get_payment_by_sale(
    sale_id: int,
    current_user: User = Depends(_staff),
    session: Session = Depends(get_session),
) -> PaymentRead:
    try:
        payment = payment_service.get_payment_by_sale(session, sale_id, actor=current_user)
    except PaymentError as exc:
        raise http_error(exc) from exc
    return _to_read(payment)


@router.post("/{payment_id}/simulate", status_code=status.HTTP_200_OK)
def simulate_webhook(
    payment_id: int,
    body: SimulateRequest,
    current_user: User = Depends(_staff),
    session: Session = Depends(get_session),
) -> dict:
    # Solo en modo mock: en 'real' este endpoint no existe.
    if not is_mock():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No encontrado")
    try:
        payment = payment_service.get_payment(session, payment_id, actor=current_user)
        # Además del modo, el pago concreto debe ser del proveedor mock.
        if payment.provider != PaymentProvider.mock:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No encontrado")
        provider = get_wompi_provider()
        evento = provider.build_event(
            transaction_id=payment.wompi_transaction_id,
            status="APPROVED" if body.result == "approved" else "DECLINED",
            referencia=payment.referencia,
            monto_centavos=payment.monto_centavos,
        )
        payment_service.process_webhook(session, evento)
    except PaymentError as exc:
        raise http_error(exc) from exc
    return {"ok": True}
