"""Acceso a datos del kardex (movimientos). Solo queries; sin lógica de negocio.

No hace commit: la frontera transaccional la controla el service.
"""

from datetime import datetime

from sqlmodel import Session, select

from app.models.inventory_movement import InventoryMovement, MovementType


def add(session: Session, movement: InventoryMovement) -> InventoryMovement:
    session.add(movement)
    session.flush()
    return movement


def list_for_product(session: Session, product_id: int) -> list[InventoryMovement]:
    stmt = (
        select(InventoryMovement)
        .where(InventoryMovement.product_id == product_id)
        .order_by(InventoryMovement.created_at.desc(), InventoryMovement.id.desc())
    )
    return list(session.exec(stmt).all())


def list_all(
    session: Session,
    *,
    product_id: int | None = None,
    tipo: MovementType | None = None,
    desde: datetime | None = None,
    hasta: datetime | None = None,
    offset: int = 0,
    limit: int = 100,
) -> list[InventoryMovement]:
    stmt = select(InventoryMovement)
    if product_id is not None:
        stmt = stmt.where(InventoryMovement.product_id == product_id)
    if tipo is not None:
        stmt = stmt.where(InventoryMovement.tipo == tipo)
    if desde is not None:
        stmt = stmt.where(InventoryMovement.created_at >= desde)
    if hasta is not None:
        stmt = stmt.where(InventoryMovement.created_at <= hasta)
    stmt = (
        stmt.order_by(InventoryMovement.created_at.desc(), InventoryMovement.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(session.exec(stmt).all())
