"""Lógica de caja: apertura, cierre y arqueo. No conoce HTTP.

"Una sola caja abierta a la vez" es una VALIDACIÓN DE NEGOCIO (no un constraint
del esquema): se serializa con un advisory lock y se valida la existencia de otra
caja abierta. Así migrar a multi-caja no exige tocar el modelo.
"""

from datetime import UTC, datetime

from sqlmodel import Session

from app.models.cash_register_session import CashRegisterSession, CashSessionStatus
from app.models.sale import PaymentMethod
from app.models.user import User, UserRole
from app.repositories import cash_repository, sale_repository
from app.services.sales_errors import (
    CashSessionAlreadyClosed,
    CashSessionAlreadyOpen,
    CashSessionNotFound,
    ForbiddenCashSession,
    NoCashSessionOpen,
    SaleHasPendingItems,
)


def get(
    session: Session, cash_session_id: int, *, actor: User | None = None
) -> CashRegisterSession:
    cash = cash_repository.get(session, cash_session_id)
    if cash is None:
        raise CashSessionNotFound(f"Caja {cash_session_id} no encontrada")
    # El cajero solo ve su propia caja; el admin, cualquiera.
    if actor is not None and actor.role != UserRole.admin and cash.user_id != actor.id:
        raise ForbiddenCashSession("No puedes ver una caja que no es tuya")
    return cash


def get_current(session: Session) -> CashRegisterSession:
    cash = cash_repository.get_open(session)
    if cash is None:
        raise NoCashSessionOpen("No hay caja abierta")
    return cash


def list_sessions(session: Session, *, actor: User) -> list[CashRegisterSession]:
    # El cajero ve solo sus cajas; el admin, todas.
    user_id = None if actor.role == UserRole.admin else actor.id
    return cash_repository.list_all(session, user_id=user_id)


def open_session(
    session: Session, *, monto_inicial_centavos: int, user_id: int
) -> CashRegisterSession:
    # Serializa aperturas concurrentes (se libera al commit); luego valida.
    cash_repository.acquire_open_lock(session)
    if cash_repository.get_open(session) is not None:
        raise CashSessionAlreadyOpen("Ya hay una caja abierta")
    cash = CashRegisterSession(
        user_id=user_id,
        monto_inicial_centavos=monto_inicial_centavos,
        status=CashSessionStatus.abierta,
    )
    cash_repository.add(session, cash)
    session.commit()
    session.refresh(cash)
    return cash


def expected_cash(session: Session, cash_session: CashRegisterSession) -> int:
    """Efectivo esperado en caja = monto inicial + ventas pagadas en efectivo."""
    ventas_efectivo = sale_repository.sum_paid_by_method(
        session, cash_session.id, PaymentMethod.efectivo
    )
    return cash_session.monto_inicial_centavos + ventas_efectivo


def close_session(
    session: Session,
    cash_session_id: int,
    *,
    efectivo_contado_centavos: int,
    actor: User,
    nota_cierre: str | None = None,
) -> CashRegisterSession:
    cash = get(session, cash_session_id)
    # El cajero solo cierra su propia caja; el admin, cualquiera.
    if actor.role != UserRole.admin and cash.user_id != actor.id:
        raise ForbiddenCashSession("No puedes cerrar una caja que no es tuya")
    if cash.status == CashSessionStatus.cerrada:
        raise CashSessionAlreadyClosed("La caja ya está cerrada")
    if sale_repository.count_unresolved(session, cash.id) > 0:
        raise SaleHasPendingItems("La caja tiene ventas con pago pendiente o en proceso")

    esperado = expected_cash(session, cash)
    cash.efectivo_esperado_centavos = esperado
    cash.efectivo_contado_centavos = efectivo_contado_centavos
    cash.diferencia_centavos = efectivo_contado_centavos - esperado
    cash.status = CashSessionStatus.cerrada
    cash.cerrada_at = datetime.now(UTC)
    cash.closed_by_user_id = actor.id
    cash.nota_cierre = nota_cierre
    cash_repository.add(session, cash)
    session.commit()
    session.refresh(cash)
    return cash


def session_summary(session: Session, cash_session_id: int) -> dict[str, int]:
    """Totales de ventas pagadas por método (arqueo informativo)."""
    return sale_repository.totals_by_method(session, cash_session_id)
