"""Endpoints de caja. Orquestan; la lógica vive en cash_service.

Permisos: cajero y admin operan caja (cajero la suya; admin cualquiera).
"""

from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.core.deps import require_role
from app.db.session import get_session
from app.models.user import User, UserRole
from app.routers._errors import http_error
from app.schemas.cash import (
    CashSessionClose,
    CashSessionDetail,
    CashSessionOpen,
    CashSessionRead,
)
from app.services import cash_service
from app.services.sales_errors import SaleError

router = APIRouter(prefix="/cash", tags=["cash"])

_staff = require_role(UserRole.admin, UserRole.cajero)


@router.post(
    "/sessions",
    response_model=CashSessionRead,
    status_code=status.HTTP_201_CREATED,
)
def open_cash_session(
    body: CashSessionOpen,
    current_user: User = Depends(_staff),
    session: Session = Depends(get_session),
) -> CashSessionRead:
    try:
        return cash_service.open_session(
            session,
            monto_inicial_centavos=body.monto_inicial_centavos,
            user_id=current_user.id,
        )
    except SaleError as exc:
        raise http_error(exc) from exc


@router.get("/sessions/current", response_model=CashSessionRead)
def current_cash_session(
    _: User = Depends(_staff), session: Session = Depends(get_session)
) -> CashSessionRead:
    try:
        return cash_service.get_current(session)
    except SaleError as exc:
        raise http_error(exc) from exc


@router.get("/sessions", response_model=list[CashSessionRead])
def list_cash_sessions(
    current_user: User = Depends(_staff), session: Session = Depends(get_session)
) -> list[CashSessionRead]:
    return cash_service.list_sessions(session, actor=current_user)


@router.get("/sessions/{cash_session_id}", response_model=CashSessionDetail)
def get_cash_session(
    cash_session_id: int,
    current_user: User = Depends(_staff),
    session: Session = Depends(get_session),
) -> CashSessionDetail:
    try:
        cash = cash_service.get(session, cash_session_id, actor=current_user)
    except SaleError as exc:
        raise http_error(exc) from exc
    totales = cash_service.session_summary(session, cash_session_id)
    return CashSessionDetail(**cash.model_dump(), totales_por_metodo=totales)


@router.post("/sessions/{cash_session_id}/close", response_model=CashSessionRead)
def close_cash_session(
    cash_session_id: int,
    body: CashSessionClose,
    current_user: User = Depends(_staff),
    session: Session = Depends(get_session),
) -> CashSessionRead:
    try:
        return cash_service.close_session(
            session,
            cash_session_id,
            efectivo_contado_centavos=body.efectivo_contado_centavos,
            actor=current_user,
            nota_cierre=body.nota_cierre,
        )
    except SaleError as exc:
        raise http_error(exc) from exc
