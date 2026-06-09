"""Modelo de proveedor. Datos comerciales de contacto (no PII de cliente)."""

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class Supplier(SQLModel, table=True):
    __tablename__ = "suppliers"

    id: int | None = Field(default=None, primary_key=True)
    nombre: str = Field(index=True, max_length=255)
    nit: str | None = Field(default=None, max_length=50)
    contacto_nombre: str | None = Field(default=None, max_length=255)
    telefono: str | None = Field(default=None, max_length=50)
    email: str | None = Field(default=None, max_length=255)
    direccion: str | None = Field(default=None, max_length=255)
    activo: bool = Field(default=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        nullable=False,
    )
