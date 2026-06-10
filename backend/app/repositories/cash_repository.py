"""Acceso a datos de sesiones de caja. Solo queries; sin commit."""

from sqlalchemy import text
from sqlmodel import Session, select

from app.models.cash_register_session import CashRegisterSession, CashSessionStatus

# Clave fija para el advisory lock que serializa la apertura de caja.
_OPEN_CASH_LOCK_KEY = 4201


def acquire_open_lock(session: Session) -> None:
    """Lock transaccional para serializar la apertura de caja (se libera al commit).

    Hace cumplir "una sola caja abierta" como regla de NEGOCIO sin un constraint
    estructural en el esquema (que cerraría la puerta a multi-caja futura).
    """
    session.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": _OPEN_CASH_LOCK_KEY})


def get(session: Session, cash_session_id: int) -> CashRegisterSession | None:
    return session.get(CashRegisterSession, cash_session_id)


def get_open(session: Session) -> CashRegisterSession | None:
    """La caja actualmente abierta (regla de negocio: a lo sumo una)."""
    stmt = select(CashRegisterSession).where(
        CashRegisterSession.status == CashSessionStatus.abierta
    )
    return session.exec(stmt).first()


def get_open_for_update(session: Session) -> CashRegisterSession | None:
    stmt = (
        select(CashRegisterSession)
        .where(CashRegisterSession.status == CashSessionStatus.abierta)
        .with_for_update()
    )
    return session.exec(stmt).first()


def list_all(session: Session, *, user_id: int | None = None) -> list[CashRegisterSession]:
    stmt = select(CashRegisterSession)
    if user_id is not None:
        stmt = stmt.where(CashRegisterSession.user_id == user_id)
    stmt = stmt.order_by(CashRegisterSession.abierta_at.desc())
    return list(session.exec(stmt).all())


def add(session: Session, cash_session: CashRegisterSession) -> CashRegisterSession:
    session.add(cash_session)
    session.flush()
    return cash_session
