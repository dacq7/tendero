"""Webhook de Wompi. PÚBLICO (sin auth), pero valida la firma del evento.

Idempotente: reprocesar el mismo evento es un no-op. Responde 200 ante evento
válido (nuevo o repetido); 400 si la firma no valida.
"""

from fastapi import APIRouter, Depends, Request
from sqlmodel import Session

from app.db.session import get_session
from app.routers._errors import http_error
from app.services import payment_service
from app.services.payment_errors import PaymentError

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/wompi", status_code=200)
async def wompi_webhook(request: Request, session: Session = Depends(get_session)) -> dict:
    payload = await request.json()
    try:
        payment_service.process_webhook(session, payload)
    except PaymentError as exc:
        # Firma inválida → 400 (no 500). Nunca filtra detalles del secreto.
        raise http_error(exc) from exc
    return {"ok": True}
