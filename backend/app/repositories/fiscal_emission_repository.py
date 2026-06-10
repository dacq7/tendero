"""Acceso a datos de emisiones fiscales. Solo queries; sin commit."""

from sqlmodel import Session, select

from app.models.fiscal_emission import FiscalEmission


def add(session: Session, emission: FiscalEmission) -> FiscalEmission:
    session.add(emission)
    session.flush()
    return emission


def get(session: Session, emission_id: int) -> FiscalEmission | None:
    return session.get(FiscalEmission, emission_id)


def get_by_invoice(session: Session, invoice_id: int) -> FiscalEmission | None:
    return session.exec(
        select(FiscalEmission).where(FiscalEmission.invoice_id == invoice_id)
    ).first()


def get_by_invoice_for_update(session: Session, invoice_id: int) -> FiscalEmission | None:
    """Carga la emisión de la factura con bloqueo de fila (idempotencia del emit)."""
    stmt = (
        select(FiscalEmission)
        .where(FiscalEmission.invoice_id == invoice_id)
        .with_for_update()
    )
    return session.exec(stmt).first()
