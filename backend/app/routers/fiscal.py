"""Endpoints de facturación electrónica DIAN. Orquestan; lógica en *_service.

Permisos: emitir y gestionar resoluciones = SOLO admin. Consultar el estado de
emisión = admin y cajero.
"""

from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.core.deps import require_role
from app.db.session import get_session
from app.models.user import UserRole
from app.routers._errors import http_error
from app.schemas.fiscal import (
    FiscalEmissionRead,
    InvoiceResolutionCreate,
    InvoiceResolutionRead,
    InvoiceResolutionUpdate,
)
from app.services import fiscal_service, resolution_service
from app.services.fiscal_errors import FiscalError
from app.services.sales_errors import SaleError

router = APIRouter(prefix="/fiscal", tags=["fiscal"])

_admin = require_role(UserRole.admin)
_staff = require_role(UserRole.admin, UserRole.cajero)


@router.post(
    "/invoices/{invoice_id}/emit",
    response_model=FiscalEmissionRead,
    dependencies=[Depends(_admin)],
)
def emit_invoice(invoice_id: int, session: Session = Depends(get_session)) -> FiscalEmissionRead:
    try:
        return fiscal_service.emit_fiscal(session, invoice_id)
    except (FiscalError, SaleError) as exc:
        raise http_error(exc) from exc


@router.get(
    "/invoices/{invoice_id}/emission",
    response_model=FiscalEmissionRead,
    dependencies=[Depends(_staff)],
)
def get_emission(invoice_id: int, session: Session = Depends(get_session)) -> FiscalEmissionRead:
    try:
        return fiscal_service.get_emission(session, invoice_id)
    except FiscalError as exc:
        raise http_error(exc) from exc


@router.get(
    "/resolutions",
    response_model=list[InvoiceResolutionRead],
    dependencies=[Depends(_admin)],
)
def list_resolutions(session: Session = Depends(get_session)) -> list[InvoiceResolutionRead]:
    return resolution_service.list_resolutions(session)


@router.post(
    "/resolutions",
    response_model=InvoiceResolutionRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_admin)],
)
def create_resolution(
    body: InvoiceResolutionCreate, session: Session = Depends(get_session)
) -> InvoiceResolutionRead:
    try:
        return resolution_service.create_resolution(session, body)
    except FiscalError as exc:
        raise http_error(exc) from exc


@router.patch(
    "/resolutions/{resolution_id}",
    response_model=InvoiceResolutionRead,
    dependencies=[Depends(_admin)],
)
def update_resolution(
    resolution_id: int,
    body: InvoiceResolutionUpdate,
    session: Session = Depends(get_session),
) -> InvoiceResolutionRead:
    try:
        return resolution_service.set_active(session, resolution_id, body.activa)
    except FiscalError as exc:
        raise http_error(exc) from exc
