"""Paquete de modelos. Importar aquí cada modelo para que Alembic los registre."""
from app.models.user import User, UserRole

__all__ = ["User", "UserRole"]
