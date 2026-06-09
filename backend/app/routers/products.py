"""Endpoints de productos. Orquestan; la lógica vive en product_service.

Permisos: admin gestiona (escritura); admin y cajero consultan (lectura).
"""

from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from app.core.deps import require_role
from app.db.session import get_session
from app.models.user import UserRole
from app.routers._errors import http_error
from app.schemas.inventory import MovementRead
from app.schemas.product import ProductCreate, ProductRead, ProductUpdate
from app.services import inventory_service, product_service
from app.services.inventory_errors import InventoryError

router = APIRouter(prefix="/products", tags=["products"])

_admin = require_role(UserRole.admin)
_staff = require_role(UserRole.admin, UserRole.cajero)


@router.get("", response_model=list[ProductRead], dependencies=[Depends(_staff)])
def list_products(
    q: str | None = None,
    categoria: str | None = None,
    solo_activos: bool = True,
    stock_bajo: bool = False,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_session),
) -> list[ProductRead]:
    return product_service.search(
        session,
        q=q,
        categoria=categoria,
        solo_activos=solo_activos,
        stock_bajo=stock_bajo,
        offset=offset,
        limit=limit,
    )


# Debe ir ANTES de /{product_id} para no ser capturado como id.
@router.get(
    "/barcode/{codigo_barras}",
    response_model=ProductRead,
    dependencies=[Depends(_staff)],
)
def get_product_by_barcode(
    codigo_barras: str, session: Session = Depends(get_session)
) -> ProductRead:
    try:
        return product_service.get_by_barcode(session, codigo_barras)
    except InventoryError as exc:
        raise http_error(exc) from exc


@router.get("/{product_id}", response_model=ProductRead, dependencies=[Depends(_staff)])
def get_product(product_id: int, session: Session = Depends(get_session)) -> ProductRead:
    try:
        return product_service.get(session, product_id)
    except InventoryError as exc:
        raise http_error(exc) from exc


@router.get(
    "/{product_id}/kardex",
    response_model=list[MovementRead],
    dependencies=[Depends(_staff)],
)
def get_product_kardex(
    product_id: int, session: Session = Depends(get_session)
) -> list[MovementRead]:
    try:
        return inventory_service.product_kardex(session, product_id)
    except InventoryError as exc:
        raise http_error(exc) from exc


@router.post(
    "",
    response_model=ProductRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_admin)],
)
def create_product(body: ProductCreate, session: Session = Depends(get_session)) -> ProductRead:
    try:
        return product_service.create(session, body)
    except InventoryError as exc:
        raise http_error(exc) from exc


@router.patch("/{product_id}", response_model=ProductRead, dependencies=[Depends(_admin)])
def update_product(
    product_id: int, body: ProductUpdate, session: Session = Depends(get_session)
) -> ProductRead:
    try:
        return product_service.update(session, product_id, body)
    except InventoryError as exc:
        raise http_error(exc) from exc


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(_admin)],
)
def delete_product(product_id: int, session: Session = Depends(get_session)) -> None:
    try:
        product_service.deactivate(session, product_id)
    except InventoryError as exc:
        raise http_error(exc) from exc
