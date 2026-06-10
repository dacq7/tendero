"""Acceso a datos de facturas. Solo queries; sin commit."""

from sqlmodel import Session, select

from app.models.invoice import Invoice
from app.models.sale import Sale


def add(session: Session, invoice: Invoice) -> Invoice:
    session.add(invoice)
    session.flush()
    return invoice


def get(session: Session, invoice_id: int) -> Invoice | None:
    return session.get(Invoice, invoice_id)


def get_by_sale(session: Session, sale_id: int) -> Invoice | None:
    return session.exec(select(Invoice).where(Invoice.sale_id == sale_id)).first()


def get_by_numero(session: Session, numero_completo: str) -> Invoice | None:
    return session.exec(select(Invoice).where(Invoice.numero_completo == numero_completo)).first()


def list_all(
    session: Session, *, user_id: int | None = None, offset: int = 0, limit: int = 100
) -> list[Invoice]:
    stmt = select(Invoice)
    if user_id is not None:
        # El cajero solo ve facturas de SUS ventas.
        stmt = stmt.join(Sale, Sale.id == Invoice.sale_id).where(Sale.user_id == user_id)
    stmt = stmt.order_by(Invoice.created_at.desc(), Invoice.id.desc()).offset(offset).limit(limit)
    return list(session.exec(stmt).all())
