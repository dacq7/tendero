"""Lógica de consulta de facturas. La emisión la hace sale_service (atómica).

El cajero solo ve facturas de sus propias ventas; el admin, todas.
"""

from sqlmodel import Session

from app.models.invoice import Invoice
from app.models.user import User, UserRole
from app.repositories import invoice_repository, sale_repository
from app.services.sales_errors import ForbiddenSale, InvoiceNotFound


def _assert_can_view(session: Session, invoice: Invoice, actor: User) -> None:
    if actor.role == UserRole.admin:
        return
    sale = sale_repository.get(session, invoice.sale_id)
    if sale is None or sale.user_id != actor.id:
        raise ForbiddenSale("No puedes ver una factura que no es tuya")


def get(session: Session, invoice_id: int, *, actor: User) -> Invoice:
    invoice = invoice_repository.get(session, invoice_id)
    if invoice is None:
        raise InvoiceNotFound(f"Factura {invoice_id} no encontrada")
    _assert_can_view(session, invoice, actor)
    return invoice


def get_by_numero(session: Session, numero_completo: str, *, actor: User) -> Invoice:
    invoice = invoice_repository.get_by_numero(session, numero_completo)
    if invoice is None:
        raise InvoiceNotFound(f"No hay factura con número {numero_completo}")
    _assert_can_view(session, invoice, actor)
    return invoice


def list_invoices(
    session: Session, *, actor: User, offset: int = 0, limit: int = 100
) -> list[Invoice]:
    user_id = None if actor.role == UserRole.admin else actor.id
    return invoice_repository.list_all(session, user_id=user_id, offset=offset, limit=limit)
