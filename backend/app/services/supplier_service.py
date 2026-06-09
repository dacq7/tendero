"""Lógica de proveedores. No conoce HTTP: lanza errores de dominio.

Controla la frontera transaccional (commit) ya que los repositories no lo hacen.
"""

from sqlmodel import Session

from app.models.supplier import Supplier
from app.repositories import supplier_repository
from app.schemas.supplier import SupplierCreate, SupplierUpdate
from app.services.inventory_errors import SupplierNotFound


def get(session: Session, supplier_id: int) -> Supplier:
    supplier = supplier_repository.get(session, supplier_id)
    if supplier is None:
        raise SupplierNotFound(f"Proveedor {supplier_id} no encontrado")
    return supplier


def list_(session: Session, *, solo_activos: bool = True) -> list[Supplier]:
    return supplier_repository.list_all(session, solo_activos=solo_activos)


def create(session: Session, data: SupplierCreate) -> Supplier:
    supplier = Supplier(
        nombre=data.nombre,
        nit=data.nit,
        contacto_nombre=data.contacto_nombre,
        telefono=data.telefono,
        email=data.email,
        direccion=data.direccion,
    )
    supplier_repository.add(session, supplier)
    session.commit()
    session.refresh(supplier)
    return supplier


def update(session: Session, supplier_id: int, data: SupplierUpdate) -> Supplier:
    supplier = get(session, supplier_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(supplier, field, value)
    supplier_repository.add(session, supplier)
    session.commit()
    session.refresh(supplier)
    return supplier


def deactivate(session: Session, supplier_id: int) -> None:
    """Baja lógica: conserva el histórico de productos asociados."""
    supplier = get(session, supplier_id)
    supplier.activo = False
    supplier_repository.add(session, supplier)
    session.commit()
