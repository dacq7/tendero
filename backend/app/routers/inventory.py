"""Endpoints de inventario: movimientos (kardex), entradas y alertas.

Permisos: admin registra movimientos/entradas; admin y cajero consultan.
El usuario autenticado queda registrado en cada movimiento (auditoría).
"""

from datetime import datetime

from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from app.core.deps import require_role
from app.db.session import get_session
from app.models.inventory_movement import MovementType
from app.models.user import User, UserRole
from app.routers._errors import http_error
from app.schemas.inventory import (
    GoodsEntryCreate,
    GoodsEntryRead,
    LowStockAlert,
    MovementCreate,
    MovementRead,
)
from app.services import inventory_service
from app.services.inventory_errors import InventoryError

router = APIRouter(prefix="/inventory", tags=["inventory"])

_admin = require_role(UserRole.admin)
_staff = require_role(UserRole.admin, UserRole.cajero)


@router.post(
    "/movements",
    response_model=MovementRead,
    status_code=status.HTTP_201_CREATED,
)
def create_movement(
    body: MovementCreate,
    current_user: User = Depends(_admin),
    session: Session = Depends(get_session),
) -> MovementRead:
    try:
        return inventory_service.register_movement(session, body, user_id=current_user.id)
    except InventoryError as exc:
        raise http_error(exc) from exc


@router.post(
    "/entries",
    response_model=GoodsEntryRead,
    status_code=status.HTTP_201_CREATED,
)
def create_goods_entry(
    body: GoodsEntryCreate,
    current_user: User = Depends(_admin),
    session: Session = Depends(get_session),
) -> GoodsEntryRead:
    try:
        movimientos = inventory_service.register_goods_entry(session, body, user_id=current_user.id)
        return GoodsEntryRead(movimientos=movimientos)
    except InventoryError as exc:
        raise http_error(exc) from exc


@router.get(
    "/alerts/low-stock",
    response_model=list[LowStockAlert],
    dependencies=[Depends(_staff)],
)
def low_stock(session: Session = Depends(get_session)) -> list[LowStockAlert]:
    return inventory_service.low_stock_alerts(session)


@router.get(
    "/movements",
    response_model=list[MovementRead],
    dependencies=[Depends(_staff)],
)
def list_movements(
    product_id: int | None = None,
    tipo: MovementType | None = None,
    desde: datetime | None = None,
    hasta: datetime | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    session: Session = Depends(get_session),
) -> list[MovementRead]:
    return inventory_service.list_movements(
        session,
        product_id=product_id,
        tipo=tipo,
        desde=desde,
        hasta=hasta,
        offset=offset,
        limit=limit,
    )
