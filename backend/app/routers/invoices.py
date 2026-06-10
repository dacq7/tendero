"""Endpoints de facturas (historial, reimpresión). Permisos: admin y cajero."""

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.core.deps import require_role
from app.db.session import get_session
from app.models.user import User, UserRole
from app.routers._errors import http_error
from app.schemas.invoice import InvoiceRead
from app.services import invoice_service
from app.services.sales_errors import SaleError

router = APIRouter(prefix="/invoices", tags=["invoices"])

_staff = require_role(UserRole.admin, UserRole.cajero)


@router.get("", response_model=list[InvoiceRead])
def list_invoices(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    current_user: User = Depends(_staff),
    session: Session = Depends(get_session),
) -> list[InvoiceRead]:
    return invoice_service.list_invoices(session, actor=current_user, offset=offset, limit=limit)


@router.get("/by-numero/{numero_completo}", response_model=InvoiceRead)
def get_invoice_by_numero(
    numero_completo: str,
    current_user: User = Depends(_staff),
    session: Session = Depends(get_session),
) -> InvoiceRead:
    try:
        return invoice_service.get_by_numero(session, numero_completo, actor=current_user)
    except SaleError as exc:
        raise http_error(exc) from exc


@router.get("/{invoice_id}", response_model=InvoiceRead)
def get_invoice(
    invoice_id: int,
    current_user: User = Depends(_staff),
    session: Session = Depends(get_session),
) -> InvoiceRead:
    try:
        return invoice_service.get(session, invoice_id, actor=current_user)
    except SaleError as exc:
        raise http_error(exc) from exc
