"""Acceso a datos de ventas. Solo queries; sin commit."""

from sqlalchemy import func
from sqlmodel import Session, select

from app.models.sale import PaymentMethod, Sale, SaleItem, SaleStatus


def get(session: Session, sale_id: int) -> Sale | None:
    return session.get(Sale, sale_id)


def add(session: Session, sale: Sale) -> Sale:
    session.add(sale)
    session.flush()
    return sale


def add_item(session: Session, item: SaleItem) -> SaleItem:
    session.add(item)
    session.flush()
    return item


def items_for_sale(session: Session, sale_id: int) -> list[SaleItem]:
    stmt = select(SaleItem).where(SaleItem.sale_id == sale_id).order_by(SaleItem.id)
    return list(session.exec(stmt).all())


def list_all(
    session: Session,
    *,
    cash_session_id: int | None = None,
    user_id: int | None = None,
    status: SaleStatus | None = None,
    offset: int = 0,
    limit: int = 100,
) -> list[Sale]:
    stmt = select(Sale)
    if cash_session_id is not None:
        stmt = stmt.where(Sale.cash_session_id == cash_session_id)
    if user_id is not None:
        stmt = stmt.where(Sale.user_id == user_id)
    if status is not None:
        stmt = stmt.where(Sale.status == status)
    stmt = stmt.order_by(Sale.created_at.desc(), Sale.id.desc()).offset(offset).limit(limit)
    return list(session.exec(stmt).all())


def sum_paid_by_method(session: Session, cash_session_id: int, metodo: PaymentMethod) -> int:
    """Suma de totales de ventas PAGADAS de un método en una caja (0 si ninguna)."""
    stmt = select(func.coalesce(func.sum(Sale.total_centavos), 0)).where(
        Sale.cash_session_id == cash_session_id,
        Sale.status == SaleStatus.pagada,
        Sale.metodo_pago == metodo,
    )
    return int(session.exec(stmt).one())


def totals_by_method(session: Session, cash_session_id: int) -> dict[str, int]:
    """Totales de ventas pagadas agrupados por método (para el arqueo informativo)."""
    stmt = (
        select(Sale.metodo_pago, func.coalesce(func.sum(Sale.total_centavos), 0))
        .where(
            Sale.cash_session_id == cash_session_id,
            Sale.status == SaleStatus.pagada,
        )
        .group_by(Sale.metodo_pago)
    )
    return {str(metodo): int(total) for metodo, total in session.exec(stmt).all()}


def count_pending(session: Session, cash_session_id: int) -> int:
    stmt = select(func.count()).where(
        Sale.cash_session_id == cash_session_id,
        Sale.status == SaleStatus.pendiente,
    )
    return int(session.exec(stmt).one())
