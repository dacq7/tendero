"""Excepciones de dominio del módulo de inventario.

Los services lanzan estas; los routers las traducen a HTTP (ver app/routers/_errors.py).
No conocen HTTP, igual que AuthError en el flujo de auth.
"""


class InventoryError(Exception):
    """Base de los errores de dominio de inventario."""


class SupplierNotFound(InventoryError):
    pass


class ProductNotFound(InventoryError):
    pass


class DuplicateSku(InventoryError):
    pass


class DuplicateBarcode(InventoryError):
    pass


class InsufficientStock(InventoryError):
    pass


class InvalidQuantity(InventoryError):
    pass


class InvalidCost(InventoryError):
    pass
