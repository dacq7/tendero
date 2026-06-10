"""Tests unitarios PUROS del cálculo de IVA y totales por línea (sin DB)."""

from app.models.product import IvaRate
from app.services import sale_pricing


def test_iva_19() -> None:
    # 1 unidad a $1000 (100000 centavos), IVA 19%.
    r = sale_pricing.line_totals(100000, IvaRate.tarifa_19, 1000)
    assert r.base_centavos == 100000
    assert r.iva_bps == 1900
    assert r.iva_centavos == 19000
    assert r.total_linea_centavos == 119000


def test_iva_5() -> None:
    r = sale_pricing.line_totals(100000, IvaRate.tarifa_5, 1000)
    assert r.iva_centavos == 5000
    assert r.total_linea_centavos == 105000


def test_exento_y_tarifa_0_no_causan_iva() -> None:
    for rate in (IvaRate.exento, IvaRate.tarifa_0):
        r = sale_pricing.line_totals(100000, rate, 1000)
        assert r.iva_centavos == 0
        assert r.total_linea_centavos == 100000


def test_cantidad_granel_milesimas() -> None:
    # 0,5 kg (500 milésimas) a $2000/kg (200000), IVA 19%.
    r = sale_pricing.line_totals(200000, IvaRate.tarifa_19, 500)
    assert r.base_centavos == 100000  # 200000 * 500 / 1000
    assert r.iva_centavos == 19000
    assert r.total_linea_centavos == 119000


def test_redondeo_half_up_en_iva() -> None:
    # base 333 centavos * 19% = 63.27 → half-up 63.
    r = sale_pricing.line_totals(333, IvaRate.tarifa_19, 1000)
    assert r.base_centavos == 333
    assert r.iva_centavos == 63  # round_half_up(333*1900, 10000) = round(632700/10000)=63


def test_totales_venta_suman_lineas_sin_descuadre() -> None:
    lineas = [
        sale_pricing.line_totals(333, IvaRate.tarifa_19, 1000),  # base 333, iva 63
        sale_pricing.line_totals(100000, IvaRate.tarifa_5, 1000),  # base 100000, iva 5000
        sale_pricing.line_totals(50000, IvaRate.exento, 2000),  # base 100000, iva 0
    ]
    totals = sale_pricing.sale_totals(lineas)
    assert totals.subtotal_centavos == 333 + 100000 + 100000
    assert totals.iva_total_centavos == 63 + 5000 + 0
    assert totals.total_centavos == totals.subtotal_centavos + totals.iva_total_centavos
