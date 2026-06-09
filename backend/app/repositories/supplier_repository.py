"""Acceso a datos de proveedores. Solo queries; sin lógica de negocio.

No hace commit: la frontera transaccional la controla el service.
"""

from sqlmodel import Session, select

from app.models.supplier import Supplier


def get(session: Session, supplier_id: int) -> Supplier | None:
    return session.get(Supplier, supplier_id)


def list_all(session: Session, *, solo_activos: bool = True) -> list[Supplier]:
    stmt = select(Supplier).order_by(Supplier.nombre)
    if solo_activos:
        stmt = stmt.where(Supplier.activo)
    return list(session.exec(stmt).all())


def add(session: Session, supplier: Supplier) -> Supplier:
    """Inserta o actualiza (flush para asignar id y disparar constraints)."""
    session.add(supplier)
    session.flush()
    return supplier
