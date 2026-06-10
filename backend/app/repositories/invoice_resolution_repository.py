"""Acceso a datos de resoluciones DIAN. Solo queries; sin commit."""

from sqlmodel import Session, select

from app.models.invoice_resolution import InvoiceResolution


def get(session: Session, resolution_id: int) -> InvoiceResolution | None:
    return session.get(InvoiceResolution, resolution_id)


def get_active(session: Session) -> InvoiceResolution | None:
    return session.exec(select(InvoiceResolution).where(InvoiceResolution.activa)).first()


def lock_active(session: Session) -> InvoiceResolution | None:
    """Resolución activa con bloqueo de fila (para asignar número fiscal sin huecos)."""
    stmt = select(InvoiceResolution).where(InvoiceResolution.activa).with_for_update()
    return session.exec(stmt).first()


def list_all(session: Session) -> list[InvoiceResolution]:
    return list(session.exec(select(InvoiceResolution).order_by(InvoiceResolution.id.desc())).all())


def add(session: Session, resolution: InvoiceResolution) -> InvoiceResolution:
    session.add(resolution)
    session.flush()
    return resolution
