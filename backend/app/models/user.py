"""Modelo de usuario: dueño (admin) y operador de mostrador (cajero)."""
from datetime import datetime, timezone
from enum import Enum

from sqlmodel import Field, SQLModel


class UserRole(str, Enum):
    admin = "admin"
    cajero = "cajero"


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True, max_length=255)
    full_name: str = Field(max_length=255)
    hashed_password: str = Field(max_length=255)
    role: UserRole = Field(default=UserRole.cajero)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
