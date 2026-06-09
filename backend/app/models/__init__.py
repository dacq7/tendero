"""Paquete de modelos. Importar aquí cada modelo para que Alembic los registre."""

from app.models.inventory_movement import InventoryMovement, MovementType
from app.models.product import IVA_RATE_BPS, IvaRate, Product, ProductUnit
from app.models.supplier import Supplier
from app.models.user import User, UserRole

__all__ = [
    "IVA_RATE_BPS",
    "InventoryMovement",
    "IvaRate",
    "MovementType",
    "Product",
    "ProductUnit",
    "Supplier",
    "User",
    "UserRole",
]
