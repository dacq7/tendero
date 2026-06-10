"""Acceso a datos de pagos. Solo queries; sin commit."""

from sqlmodel import Session, select

from app.models.payment import Payment


def add(session: Session, payment: Payment) -> Payment:
    session.add(payment)
    session.flush()
    return payment


def get(session: Session, payment_id: int) -> Payment | None:
    return session.get(Payment, payment_id)


def get_by_sale(session: Session, sale_id: int) -> Payment | None:
    return session.exec(select(Payment).where(Payment.sale_id == sale_id)).first()


def get_by_wompi_tx_for_update(session: Session, transaction_id: str) -> Payment | None:
    """Carga el pago por id de transacción con bloqueo de fila (para el webhook)."""
    stmt = select(Payment).where(Payment.wompi_transaction_id == transaction_id).with_for_update()
    return session.exec(stmt).first()
