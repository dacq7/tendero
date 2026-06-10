"""Lógica de consulta de facturas. La emisión la hace sale_service (atómica)."""

from sqlmodel import Session

from app.models.invoice import Invoice
from app.repositories import invoice_repository
from app.services.sales_errors import InvoiceNotFound


def get(session: Session, invoice_id: int) -> Invoice:
    invoice = invoice_repository.get(session, invoice_id)
    if invoice is None:
        raise InvoiceNotFound(f"Factura {invoice_id} no encontrada")
    return invoice


def get_by_numero(session: Session, numero_completo: str) -> Invoice:
    invoice = invoice_repository.get_by_numero(session, numero_completo)
    if invoice is None:
        raise InvoiceNotFound(f"No hay factura con número {numero_completo}")
    return invoice


def list_invoices(session: Session, *, offset: int = 0, limit: int = 100) -> list[Invoice]:
    return invoice_repository.list_all(session, offset=offset, limit=limit)
