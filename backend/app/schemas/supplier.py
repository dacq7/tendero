"""DTOs de proveedor. Datos comerciales de contacto."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class SupplierCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=255)
    nit: str | None = None
    contacto_nombre: str | None = None
    telefono: str | None = None
    email: EmailStr | None = None
    direccion: str | None = None


class SupplierUpdate(BaseModel):
    nombre: str | None = None
    nit: str | None = None
    contacto_nombre: str | None = None
    telefono: str | None = None
    email: EmailStr | None = None
    direccion: str | None = None
    activo: bool | None = None


class SupplierRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    nit: str | None
    contacto_nombre: str | None
    telefono: str | None
    email: str | None
    direccion: str | None
    activo: bool
    created_at: datetime
