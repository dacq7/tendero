"""DTOs de facturación electrónica. NO exponen payloads crudos del PT."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.fiscal_emission import FiscalProvider
from app.models.invoice import DianStatus


class FiscalEmissionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    invoice_id: int
    numero_fiscal_completo: str
    provider: FiscalProvider
    status: DianStatus
    cufe: str | None
    motivo_rechazo: str | None
    intentos: int
    created_at: datetime
    updated_at: datetime


class InvoiceResolutionCreate(BaseModel):
    numero_resolucion: str = Field(min_length=1, max_length=64)
    prefijo: str = Field(min_length=1, max_length=10)
    numero_desde: int = Field(ge=1)
    numero_hasta: int = Field(ge=1)
    vigencia_desde: date
    vigencia_hasta: date
    rut_nit: str = Field(min_length=1, max_length=32)
    responsabilidad: str = Field(default="52", max_length=8)
    activa: bool = True


class InvoiceResolutionUpdate(BaseModel):
    activa: bool


class InvoiceResolutionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    numero_resolucion: str
    prefijo: str
    numero_desde: int
    numero_hasta: int
    last_numero: int
    vigencia_desde: date
    vigencia_hasta: date
    rut_nit: str
    responsabilidad: str
    activa: bool
    created_at: datetime
