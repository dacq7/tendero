"""Webhook de Wompi. PÚBLICO (sin auth), pero valida la firma del evento.

Idempotente: reprocesar el mismo evento es un no-op. Responde 200 ante evento
válido (nuevo o repetido); 400 con cuerpo GENÉRICO ante cualquier rechazo (firma
inválida, replay fuera de ventana o monto que no cuadra) — no se distingue el
motivo hacia un cliente no autenticado.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlmodel import Session

from app.core.rate_limit import rate_limit, webhook_limiter
from app.db.session import get_session
from app.services import payment_service
from app.services.payment_errors import PaymentError

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post(
    "/wompi",
    status_code=200,
    dependencies=[Depends(rate_limit(webhook_limiter, "webhook"))],
)
async def wompi_webhook(request: Request, session: Session = Depends(get_session)) -> dict:
    payload = await request.json()
    try:
        payment_service.process_webhook(session, payload)
    except PaymentError as exc:
        # Mensaje genérico e idéntico para TODOS los rechazos: no revela si fue firma,
        # replay o monto. Nunca 500 ni detalles internos.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Solicitud de webhook inválida"
        ) from exc
    return {"ok": True}
