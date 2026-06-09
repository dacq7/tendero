"""Tests unitarios PUROS del costeo y márgenes (sin DB)."""

from app.services import costing


def test_margin_centavos() -> None:
    assert costing.margin_centavos(200000, 120000) == 80000
    assert costing.margin_centavos(100000, 150000) == -50000  # venta a pérdida


def test_margin_bps() -> None:
    assert costing.margin_bps(200000, 120000) == 4000  # 40% = 4000 bps
    assert costing.margin_bps(0, 0) is None  # sin precio de venta
    assert costing.margin_bps(100000, 150000) == -5000  # -50% (venta a pérdida)


def test_weighted_average_sin_stock_previo_usa_costo_entrada() -> None:
    # stock 0 → el costo es el de la entrada.
    assert costing.weighted_average_cost(0, 0, 10000, 140000) == 140000


def test_weighted_average_pondera_por_cantidad() -> None:
    # 10 u a $1000 + 10 u a $1400 → $1200 (en centavos: 100000 y 140000 → 120000).
    assert costing.weighted_average_cost(10000, 100000, 10000, 140000) == 120000


def test_weighted_average_redondea_half_up() -> None:
    # 10 u a $1000 + 5 u a $1333 → (10*1000+5*1333)/15 = 16665/15 = 1111.0
    assert costing.weighted_average_cost(10000, 100000, 5000, 133300) == 111100
    # Caso con fracción: (1*100 + 2*101)/3 = 302/3 = 100.67 → half-up 101 (centavos)
    assert costing.weighted_average_cost(1000, 10000, 2000, 10100) == 10067
