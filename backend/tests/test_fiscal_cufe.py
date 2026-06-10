"""Tests PUROS del CUFE simulado y de la decisión de aceptación del mock."""

from app.models.invoice import DianStatus
from app.models.product import IvaRate
from app.services.fiscal.cufe import compute_cufe
from app.services.fiscal.mock import MockFiscalProvider
from app.services.fiscal.provider import DocumentLine, ElectronicDocument


def _doc(**over) -> ElectronicDocument:
    base = dict(
        prefijo="SETP",
        numero_fiscal=990000001,
        numero_fiscal_completo="SETP990000001",
        numero_resolucion="DEMO-1",
        rut_nit="900000000-0",
        responsabilidad="52",
        fecha="2026-06-10",
        customer_doc=None,
        customer_nombre=None,
        subtotal_centavos=100000,
        iva_total_centavos=19000,
        total_centavos=119000,
        lineas=[
            DocumentLine(
                nombre="Gaseosa",
                cantidad_milesimas=1000,
                iva_rate=IvaRate.tarifa_19,
                iva_bps=1900,
                base_centavos=100000,
                iva_centavos=19000,
                total_linea_centavos=119000,
            )
        ],
        iva_por_tarifa={"tarifa_19": 19000},
    )
    base.update(over)
    return ElectronicDocument(**base)


def test_cufe_determinista() -> None:
    kwargs = dict(
        numero_fiscal_completo="SETP990000001",
        fecha="2026-06-10",
        subtotal_centavos=100000,
        iva_total_centavos=19000,
        total_centavos=119000,
        rut_nit="900000000-0",
        numero_resolucion="DEMO-1",
        secret="s",
    )
    a = compute_cufe(**kwargs)
    b = compute_cufe(**kwargs)
    assert a == b  # mismo input → mismo CUFE (idempotencia)
    assert len(a) == 64 and all(c in "0123456789abcdef" for c in a)  # SHA256 hex
    # Cambiar un campo cambia el CUFE.
    assert compute_cufe(**{**kwargs, "total_centavos": 1}) != a


def test_mock_acepta_documento_consistente() -> None:
    res = MockFiscalProvider().submit(_doc())
    assert res.status == DianStatus.accepted
    assert res.cufe
    assert res.pt_document_id.startswith("mock-doc-")
    assert res.motivo_rechazo is None


def test_mock_rechaza_total_incoherente() -> None:
    res = MockFiscalProvider().submit(_doc(total_centavos=999999))
    assert res.status == DianStatus.rejected
    assert res.cufe is None
    assert "total" in res.motivo_rechazo.lower()


def test_mock_rechaza_iva_por_tarifa_descuadrado() -> None:
    res = MockFiscalProvider().submit(_doc(iva_por_tarifa={"tarifa_19": 1}))
    assert res.status == DianStatus.rejected
    assert "iva por tarifa" in res.motivo_rechazo.lower()
