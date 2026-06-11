"""Deuda de Fase 1 saldada en Fase 6 B.1: concurrencia REAL de stock.

Dos salidas concurrentes sobre el MISMO producto cuya suma excede el stock: el
`SELECT FOR UPDATE` de `product_service.get_locked` debe serializarlas, de modo que
EXACTAMENTE una tenga éxito y la otra falle con InsufficientStock. El stock final
nunca queda negativo ni "pierde" una de las operaciones (sin lost update).
"""

from concurrent.futures import ThreadPoolExecutor

from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.models.inventory_movement import MovementType
from app.schemas.inventory import MovementCreate
from app.services import inventory_service
from app.services.inventory_errors import InsufficientStock
from tests.test_sales import crear_producto_con_stock


def test_dos_salidas_concurrentes_se_serializan(
    client, _engine: Engine, admin_headers: dict
) -> None:
    # Producto con 10.000 milésimas (10 uds). Dos salidas de 6.000 c/u: juntas 12.000.
    pid = crear_producto_con_stock(
        client, admin_headers, sku="CONC", stock_milesimas=10000, precio_venta_centavos=100000
    )

    def salida() -> str:
        # Cada hilo con su PROPIA sesión: ejercita el FOR UPDATE de verdad.
        with Session(_engine) as s:
            try:
                inventory_service.register_movement(
                    s,
                    MovementCreate(
                        product_id=pid,
                        tipo=MovementType.salida,
                        cantidad_milesimas=6000,
                        motivo="prueba concurrencia",
                    ),
                    user_id=None,
                )
                return "ok"
            except InsufficientStock:
                return "insuficiente"

    with ThreadPoolExecutor(max_workers=2) as pool:
        resultados = sorted(f.result() for f in [pool.submit(salida), pool.submit(salida)])

    # Exactamente una tuvo éxito y la otra fue rechazada por stock.
    assert resultados == ["insuficiente", "ok"]

    # El stock final es consistente: 10.000 − 6.000 = 4.000 (nunca negativo).
    stock = client.get(f"/products/{pid}", headers=admin_headers).json()["stock_milesimas"]
    assert stock == 4000


def test_dos_salidas_concurrentes_caben_ambas(client, _engine: Engine, admin_headers: dict) -> None:
    """Si el stock alcanza para ambas, las dos se aplican sin lost update."""
    pid = crear_producto_con_stock(
        client, admin_headers, sku="CONC2", stock_milesimas=10000, precio_venta_centavos=100000
    )

    def salida() -> None:
        with Session(_engine) as s:
            inventory_service.register_movement(
                s,
                MovementCreate(
                    product_id=pid,
                    tipo=MovementType.salida,
                    cantidad_milesimas=3000,
                    motivo="prueba concurrencia",
                ),
                user_id=None,
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        for f in [pool.submit(salida), pool.submit(salida)]:
            f.result()

    # 10.000 − 3.000 − 3.000 = 4.000: ninguna salida se perdió.
    stock = client.get(f"/products/{pid}", headers=admin_headers).json()["stock_milesimas"]
    assert stock == 4000
