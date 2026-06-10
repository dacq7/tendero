"""Interfaz `FiscalGateway` (adaptador) + DTOs del documento electrónico.

A diferencia de pagos (asíncrono por webhook), la emisión fiscal es SÍNCRONA: el
PT responde estado + CUFE en la misma llamada. La idempotencia se logra con el
estado terminal de FiscalEmission + UNIQUE(invoice_id), sin webhook.
"""

from dataclasses import dataclass
from typing import Protocol

from app.models.fiscal_emission import FiscalProvider
from app.models.invoice import DianStatus
from app.models.product import IvaRate


@dataclass(frozen=True)
class DocumentLine:
    nombre: str
    cantidad_milesimas: int
    iva_rate: IvaRate
    iva_bps: int
    base_centavos: int
    iva_centavos: int
    total_linea_centavos: int


@dataclass(frozen=True)
class ElectronicDocument:
    prefijo: str
    numero_fiscal: int
    numero_fiscal_completo: str
    numero_resolucion: str
    rut_nit: str
    responsabilidad: str
    fecha: str  # ISO date de la factura interna
    customer_doc: str | None
    customer_nombre: str | None
    subtotal_centavos: int
    iva_total_centavos: int
    total_centavos: int
    lineas: list[DocumentLine]
    # IVA agregado por tarifa (clave -> centavos); la DIAN exige el desglose.
    iva_por_tarifa: dict[str, int]


@dataclass(frozen=True)
class EmissionResult:
    status: DianStatus  # pending | accepted | rejected
    cufe: str | None
    pt_document_id: str | None
    motivo_rechazo: str | None


class FiscalGateway(Protocol):
    name: FiscalProvider

    def submit(self, doc: ElectronicDocument) -> EmissionResult: ...

    def get_status(self, pt_document_id: str) -> EmissionResult: ...
