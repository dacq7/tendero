"""Emisión fiscal idempotente. No conoce HTTP.

El número fiscal se asigna del rango de la resolución activa AL EMITIR (no al crear
la factura interna), con FOR UPDATE sobre la resolución (sin huecos). El número se
COMMITEA al reservarse: un fallo posterior del PT no lo libera (un consecutivo
entregado a un documento no se reutiliza para otro). Reintentar reusa el mismo
número; reemitir una aceptada devuelve la misma emisión (idempotente).
"""

from datetime import UTC, datetime

from sqlmodel import Session

from app.models.fiscal_emission import FiscalEmission
from app.models.invoice import DianStatus
from app.models.invoice_resolution import InvoiceResolution
from app.models.sale import SaleStatus
from app.repositories import (
    fiscal_emission_repository,
    invoice_repository,
    invoice_resolution_repository,
    sale_repository,
)
from app.services.fiscal.factory import get_fiscal_provider
from app.services.fiscal.provider import DocumentLine, ElectronicDocument
from app.services.fiscal_errors import (
    EmissionNotFound,
    InvoiceNotEmittable,
    NoActiveResolution,
    ResolutionExhausted,
    ResolutionExpired,
)
from app.services.sales_errors import InvoiceNotFound


def _validate_resolution(resolution: InvoiceResolution) -> None:
    hoy = datetime.now(UTC).date()
    if hoy < resolution.vigencia_desde or hoy > resolution.vigencia_hasta:
        raise ResolutionExpired("La resolución DIAN está fuera de vigencia")
    if resolution.last_numero + 1 > resolution.numero_hasta:
        raise ResolutionExhausted("El rango de la resolución DIAN se agotó")


def emit_fiscal(session: Session, invoice_id: int) -> FiscalEmission:
    invoice = invoice_repository.get(session, invoice_id)
    if invoice is None:
        raise InvoiceNotFound(f"Factura {invoice_id} no encontrada")
    sale = sale_repository.get(session, invoice.sale_id)
    if sale is None or sale.status != SaleStatus.pagada:
        raise InvoiceNotEmittable("Solo se emiten facturas de ventas pagadas")

    emission = fiscal_emission_repository.get_by_invoice_for_update(session, invoice_id)
    if emission is not None and emission.status == DianStatus.accepted:
        return emission  # idempotente: ya aceptada, no se reenvía

    # Un solo provider para toda la operación (nombre persistido == el que emite).
    provider = get_fiscal_provider()

    if emission is None:
        # Fase 1: reservar número fiscal del rango y persistir 'pending'. Se commitea
        # para que el número quede reservado pase lo que pase con el PT.
        resolution = invoice_resolution_repository.lock_active(session)
        if resolution is None:
            raise NoActiveResolution("No hay resolución DIAN activa configurada")
        _validate_resolution(resolution)
        resolution.last_numero += 1
        numero = resolution.last_numero
        invoice_resolution_repository.add(session, resolution)
        emission = FiscalEmission(
            invoice_id=invoice_id,
            resolution_id=resolution.id,
            prefijo=resolution.prefijo,
            numero_fiscal=numero,
            numero_fiscal_completo=f"{resolution.prefijo}{numero}",
            provider=provider.name,
            status=DianStatus.pending,
            intentos=0,
        )
        fiscal_emission_repository.add(session, emission)
        invoice.dian_status = DianStatus.pending
        invoice_repository.add(session, invoice)
        session.commit()
        session.refresh(emission)
        session.refresh(invoice)

    # Fase 2: construir el documento y transmitir (reusa el número ya asignado).
    resolution = invoice_resolution_repository.get(session, emission.resolution_id)
    doc = _build_document(session, invoice, sale, emission, resolution)
    result = provider.submit(doc)  # puede lanzar FiscalProviderUnavailable

    emission.status = result.status
    emission.cufe = result.cufe
    emission.pt_document_id = result.pt_document_id
    emission.motivo_rechazo = result.motivo_rechazo
    emission.intentos += 1
    fiscal_emission_repository.add(session, emission)
    # Caché en la factura para listados rápidos.
    invoice.dian_status = result.status
    invoice.cufe = result.cufe
    invoice_repository.add(session, invoice)
    session.commit()
    session.refresh(emission)
    return emission


def get_emission(session: Session, invoice_id: int) -> FiscalEmission:
    emission = fiscal_emission_repository.get_by_invoice(session, invoice_id)
    if emission is None:
        raise EmissionNotFound(f"La factura {invoice_id} no tiene emisión fiscal")
    return emission


def _build_document(
    session: Session,
    invoice,
    sale,
    emission: FiscalEmission,
    resolution: InvoiceResolution,
) -> ElectronicDocument:
    items = sale_repository.items_for_sale(session, sale.id)
    lineas: list[DocumentLine] = []
    iva_por_tarifa: dict[str, int] = {}
    for it in items:
        lineas.append(
            DocumentLine(
                nombre=it.nombre_snapshot,
                cantidad_milesimas=it.cantidad_milesimas,
                iva_rate=it.iva_rate_snapshot,
                iva_bps=it.iva_bps_snapshot,
                base_centavos=it.base_centavos,
                iva_centavos=it.iva_centavos,
                total_linea_centavos=it.total_linea_centavos,
            )
        )
        clave = it.iva_rate_snapshot.value
        iva_por_tarifa[clave] = iva_por_tarifa.get(clave, 0) + it.iva_centavos

    return ElectronicDocument(
        prefijo=emission.prefijo,
        numero_fiscal=emission.numero_fiscal,
        numero_fiscal_completo=emission.numero_fiscal_completo,
        numero_resolucion=resolution.numero_resolucion,
        rut_nit=resolution.rut_nit,
        responsabilidad=resolution.responsabilidad,
        fecha=invoice.created_at.date().isoformat(),
        customer_doc=sale.customer_doc,
        customer_nombre=sale.customer_nombre,
        subtotal_centavos=invoice.subtotal_centavos,
        iva_total_centavos=invoice.iva_total_centavos,
        total_centavos=invoice.total_centavos,
        lineas=lineas,
        iva_por_tarifa=iva_por_tarifa,
    )
