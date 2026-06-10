"""Gestión de resoluciones DIAN del comercio. No conoce HTTP.

Regla: a lo sumo UNA resolución activa (índice parcial único). Al activar una
nueva, se desactiva la anterior dentro de la misma transacción.
"""

from sqlmodel import Session

from app.models.invoice_resolution import InvoiceResolution
from app.repositories import invoice_resolution_repository
from app.schemas.fiscal import InvoiceResolutionCreate
from app.services.fiscal_errors import InvalidResolution, ResolutionNotFound


def list_resolutions(session: Session) -> list[InvoiceResolution]:
    return invoice_resolution_repository.list_all(session)


def get_resolution(session: Session, resolution_id: int) -> InvoiceResolution:
    res = invoice_resolution_repository.get(session, resolution_id)
    if res is None:
        raise ResolutionNotFound(f"Resolución {resolution_id} no encontrada")
    return res


def _deactivate_current(session: Session) -> None:
    actual = invoice_resolution_repository.get_active(session)
    if actual is not None:
        actual.activa = False
        invoice_resolution_repository.add(session, actual)
        session.flush()  # libera el índice parcial único antes de activar otra


def create_resolution(
    session: Session, data: InvoiceResolutionCreate
) -> InvoiceResolution:
    if data.numero_hasta < data.numero_desde:
        raise InvalidResolution("numero_hasta debe ser >= numero_desde")
    if data.vigencia_hasta < data.vigencia_desde:
        raise InvalidResolution("vigencia_hasta debe ser >= vigencia_desde")

    if data.activa:
        _deactivate_current(session)

    resolution = InvoiceResolution(
        numero_resolucion=data.numero_resolucion,
        prefijo=data.prefijo,
        numero_desde=data.numero_desde,
        numero_hasta=data.numero_hasta,
        last_numero=data.numero_desde - 1,
        vigencia_desde=data.vigencia_desde,
        vigencia_hasta=data.vigencia_hasta,
        rut_nit=data.rut_nit,
        responsabilidad=data.responsabilidad,
        activa=data.activa,
    )
    invoice_resolution_repository.add(session, resolution)
    session.commit()
    session.refresh(resolution)
    return resolution


def set_active(session: Session, resolution_id: int, activa: bool) -> InvoiceResolution:
    resolution = get_resolution(session, resolution_id)
    if activa and not resolution.activa:
        _deactivate_current(session)
    resolution.activa = activa
    invoice_resolution_repository.add(session, resolution)
    session.commit()
    session.refresh(resolution)
    return resolution
