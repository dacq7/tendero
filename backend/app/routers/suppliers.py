"""Endpoints de proveedores. Orquestan; la lógica vive en supplier_service.

Permisos: admin gestiona (escritura); admin y cajero consultan (lectura).
"""

from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.core.deps import require_role
from app.db.session import get_session
from app.models.user import UserRole
from app.routers._errors import http_error
from app.schemas.supplier import SupplierCreate, SupplierRead, SupplierUpdate
from app.services import supplier_service
from app.services.inventory_errors import InventoryError

router = APIRouter(prefix="/suppliers", tags=["suppliers"])

_admin = require_role(UserRole.admin)
_staff = require_role(UserRole.admin, UserRole.cajero)


@router.get("", response_model=list[SupplierRead], dependencies=[Depends(_staff)])
def list_suppliers(
    solo_activos: bool = True,
    session: Session = Depends(get_session),
) -> list[SupplierRead]:
    return supplier_service.list_(session, solo_activos=solo_activos)


@router.get("/{supplier_id}", response_model=SupplierRead, dependencies=[Depends(_staff)])
def get_supplier(supplier_id: int, session: Session = Depends(get_session)) -> SupplierRead:
    try:
        return supplier_service.get(session, supplier_id)
    except InventoryError as exc:
        raise http_error(exc) from exc


@router.post(
    "",
    response_model=SupplierRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_admin)],
)
def create_supplier(body: SupplierCreate, session: Session = Depends(get_session)) -> SupplierRead:
    return supplier_service.create(session, body)


@router.patch("/{supplier_id}", response_model=SupplierRead, dependencies=[Depends(_admin)])
def update_supplier(
    supplier_id: int, body: SupplierUpdate, session: Session = Depends(get_session)
) -> SupplierRead:
    try:
        return supplier_service.update(session, supplier_id, body)
    except InventoryError as exc:
        raise http_error(exc) from exc


@router.delete(
    "/{supplier_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(_admin)],
)
def delete_supplier(supplier_id: int, session: Session = Depends(get_session)) -> None:
    try:
        supplier_service.deactivate(session, supplier_id)
    except InventoryError as exc:
        raise http_error(exc) from exc
