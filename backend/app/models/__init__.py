"""Paquete de modelos. Importar aquí cada modelo para que Alembic los registre."""

from app.models.cash_register_session import CashRegisterSession, CashSessionStatus
from app.models.inventory_movement import InventoryMovement, MovementType
from app.models.invoice import DianStatus, Invoice
from app.models.invoice_sequence import InvoiceSequence
from app.models.product import IVA_RATE_BPS, IvaRate, Product, ProductUnit
from app.models.sale import PaymentMethod, Sale, SaleItem, SaleStatus
from app.models.supplier import Supplier
from app.models.user import User, UserRole

__all__ = [
    "IVA_RATE_BPS",
    "CashRegisterSession",
    "CashSessionStatus",
    "DianStatus",
    "InventoryMovement",
    "Invoice",
    "InvoiceSequence",
    "IvaRate",
    "MovementType",
    "PaymentMethod",
    "Product",
    "ProductUnit",
    "Sale",
    "SaleItem",
    "SaleStatus",
    "Supplier",
    "User",
    "UserRole",
]
