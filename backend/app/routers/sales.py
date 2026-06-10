"""Endpoints de ventas. Orquestan; la lógica atómica vive en sale_service.

Permisos: cajero y admin venden; el cajero ve solo sus ventas, el admin todas.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.core.deps import require_role
from app.db.session import get_session
from app.models.invoice import Invoice
from app.models.sale import Sale, SaleItem, SaleStatus
from app.models.user import User, UserRole
from app.routers._errors import http_error
from app.schemas.invoice import InvoiceRead
from app.schemas.sale import (
    SaleCreate,
    SaleItemRead,
    SaleRead,
    SaleSummary,
)
from app.services import sale_service
from app.services.inventory_errors import InventoryError
from app.services.sales_errors import SaleError

router = APIRouter(prefix="/sales", tags=["sales"])

_staff = require_role(UserRole.admin, UserRole.cajero)


def _to_read(sale: Sale, items: list[SaleItem], invoice: Invoice) -> SaleRead:
    return SaleRead(
        **sale.model_dump(),
        items=[SaleItemRead.model_validate(i) for i in items],
        invoice=InvoiceRead.model_validate(invoice),
    )


def _ensure_can_view(sale: Sale, actor: User) -> None:
    if actor.role != UserRole.admin and sale.user_id != actor.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes ver una venta que no es tuya",
        )


@router.post("", response_model=SaleRead, status_code=status.HTTP_201_CREATED)
def create_sale(
    body: SaleCreate,
    current_user: User = Depends(_staff),
    session: Session = Depends(get_session),
) -> SaleRead:
    try:
        sale = sale_service.create_sale(session, body, user_id=current_user.id)
        detail = sale_service.sale_detail(session, sale.id)
    except (SaleError, InventoryError) as exc:
        raise http_error(exc) from exc
    return _to_read(*detail)


@router.get("", response_model=list[SaleSummary])
def list_sales(
    cash_session_id: int | None = None,
    status_filter: SaleStatus | None = None,
    current_user: User = Depends(_staff),
    session: Session = Depends(get_session),
) -> list[SaleSummary]:
    return sale_service.list_sales(
        session,
        actor=current_user,
        cash_session_id=cash_session_id,
        status=status_filter,
    )


@router.get("/{sale_id}", response_model=SaleRead)
def get_sale(
    sale_id: int,
    current_user: User = Depends(_staff),
    session: Session = Depends(get_session),
) -> SaleRead:
    try:
        detail = sale_service.sale_detail(session, sale_id)
    except SaleError as exc:
        raise http_error(exc) from exc
    _ensure_can_view(detail[0], current_user)
    return _to_read(*detail)
