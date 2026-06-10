"""MockFiscalProvider: camino de demostración del portafolio.

Mapea la factura a un documento electrónico, genera un CUFE simulado determinista
y decide aceptación de forma EXPLICABLE (no aleatoria): acepta si el documento es
consistente; rechaza si los totales o el IVA por tarifa no cuadran. SIN validez
fiscal — solo demostración.
"""

from app.core.config import settings
from app.models.fiscal_emission import FiscalProvider
from app.models.invoice import DianStatus
from app.services.fiscal.cufe import compute_cufe
from app.services.fiscal.provider import ElectronicDocument, EmissionResult


class MockFiscalProvider:
    name = FiscalProvider.mock

    def submit(self, doc: ElectronicDocument) -> EmissionResult:
        motivo = _inconsistencia(doc)
        if motivo is not None:
            return EmissionResult(
                status=DianStatus.rejected, cufe=None, pt_document_id=None, motivo_rechazo=motivo
            )
        cufe = compute_cufe(
            numero_fiscal_completo=doc.numero_fiscal_completo,
            fecha=doc.fecha,
            subtotal_centavos=doc.subtotal_centavos,
            iva_total_centavos=doc.iva_total_centavos,
            total_centavos=doc.total_centavos,
            rut_nit=doc.rut_nit,
            numero_resolucion=doc.numero_resolucion,
            secret=settings.fiscal_cufe_secret,
        )
        return EmissionResult(
            status=DianStatus.accepted,
            cufe=cufe,
            pt_document_id=f"mock-doc-{cufe[:8]}",
            motivo_rechazo=None,
        )

    def get_status(self, pt_document_id: str) -> EmissionResult:
        # El mock no guarda estado: la verdad vive en fiscal_emissions.
        return EmissionResult(
            status=DianStatus.accepted,
            cufe=None,
            pt_document_id=pt_document_id,
            motivo_rechazo=None,
        )


def _inconsistencia(doc: ElectronicDocument) -> str | None:
    """Devuelve el motivo de rechazo si el documento es inconsistente, o None."""
    if doc.total_centavos != doc.subtotal_centavos + doc.iva_total_centavos:
        return "El total no cuadra con subtotal + IVA"
    if sum(doc.iva_por_tarifa.values()) != doc.iva_total_centavos:
        return "El IVA por tarifa no cuadra con el IVA total"
    if not doc.lineas:
        return "El documento no tiene líneas"
    return None
