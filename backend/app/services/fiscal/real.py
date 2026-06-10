"""RealFiscalProvider: mapea al API REST de un Proveedor Tecnológico genérico
(tipo Alanube/Factus). Bien diseñado pero NO se ejecuta sin credenciales reales
(proyecto de portafolio): si faltan, falla con FiscalProviderUnavailable. Las
credenciales del PT viven SOLO en el servidor.
"""

import httpx

from app.core.config import settings
from app.models.fiscal_emission import FiscalProvider
from app.models.invoice import DianStatus
from app.services.fiscal.provider import ElectronicDocument, EmissionResult
from app.services.fiscal_errors import FiscalProviderUnavailable

_TIMEOUT = 20.0

# Estado del PT (string) → nuestro DianStatus. Cada PT usa sus etiquetas; este
# mapeo se ajustaría al PT concreto al integrarlo.
_PT_STATUS_MAP = {
    "ACCEPTED": DianStatus.accepted,
    "APPROVED": DianStatus.accepted,
    "PENDING": DianStatus.pending,
    "PROCESSING": DianStatus.pending,
    "REJECTED": DianStatus.rejected,
    "ERROR": DianStatus.rejected,
}


class RealFiscalProvider:
    name = FiscalProvider.pt

    def _require_creds(self) -> tuple[str, str]:
        if not settings.fiscal_pt_api_url or not settings.fiscal_pt_api_key:
            raise FiscalProviderUnavailable(
                "Credenciales del PT no configuradas: el proveedor real no puede operar. "
                "Usa FISCAL_PROVIDER=mock para la demo."
            )
        return settings.fiscal_pt_api_url, settings.fiscal_pt_api_key

    def submit(self, doc: ElectronicDocument) -> EmissionResult:
        api_url, api_key = self._require_creds()
        body = _to_pt_payload(doc)
        # Cualquier error HTTP se traduce a un error de dominio: NUNCA un 500 que
        # filtre la URL del PT, la api_key de las cabeceras o el cuerpo de error.
        try:
            resp = httpx.post(
                f"{api_url}/invoices",
                json=body,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    # Idempotencia: un reintento de red no duplica el documento.
                    "Idempotency-Key": doc.numero_fiscal_completo,
                },
                timeout=_TIMEOUT,
            )
            resp.raise_for_status()
            return _parse_pt_response(resp.json())
        except httpx.HTTPError as exc:
            raise FiscalProviderUnavailable("Error comunicándose con el PT") from exc

    def get_status(self, pt_document_id: str) -> EmissionResult:
        api_url, api_key = self._require_creds()
        try:
            resp = httpx.get(
                f"{api_url}/invoices/{pt_document_id}",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=_TIMEOUT,
            )
            resp.raise_for_status()
            return _parse_pt_response(resp.json())
        except httpx.HTTPError as exc:
            raise FiscalProviderUnavailable("Error comunicándose con el PT") from exc


def _to_pt_payload(doc: ElectronicDocument) -> dict:
    """Mapea el documento a la estructura UBL-like que esperan los PT REST."""
    return {
        "resolution": {
            "number": doc.numero_resolucion,
            "prefix": doc.prefijo,
            "consecutive": doc.numero_fiscal,
        },
        "issuer": {"nit": doc.rut_nit, "responsabilidad": doc.responsabilidad},
        "customer": {"document": doc.customer_doc, "name": doc.customer_nombre},
        "date": doc.fecha,
        "totals": {
            "subtotal": doc.subtotal_centavos,
            "tax": doc.iva_total_centavos,
            "total": doc.total_centavos,
            "tax_by_rate": doc.iva_por_tarifa,
        },
        "lines": [
            {
                "name": ln.nombre,
                "quantity_milli": ln.cantidad_milesimas,
                "tax_rate_bps": ln.iva_bps,
                "base": ln.base_centavos,
                "tax": ln.iva_centavos,
                "total": ln.total_linea_centavos,
            }
            for ln in doc.lineas
        ],
    }


def _parse_pt_response(data: dict) -> EmissionResult:
    status = _PT_STATUS_MAP.get(str(data.get("status", "")).upper(), DianStatus.pending)
    return EmissionResult(
        status=status,
        cufe=data.get("cufe"),
        pt_document_id=str(data.get("id")) if data.get("id") is not None else None,
        motivo_rechazo=data.get("reason"),
    )
