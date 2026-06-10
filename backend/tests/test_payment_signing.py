"""Tests PUROS de las firmas Wompi (integridad y checksum de evento)."""

import hashlib

import pytest

from app.services.payment_errors import InvalidSignature
from app.services.payments import provider as provider_mod
from app.services.payments.signing import event_checksum, integrity_signature


def test_integrity_signature_es_sha256_esperado() -> None:
    # Vector conocido: SHA256(referencia + monto + moneda + secreto).
    firma = integrity_signature("SALE-000001", 119000, "COP", "secreto")
    esperado = hashlib.sha256(b"SALE-000001119000COPsecreto").hexdigest()
    assert firma == esperado


def test_event_checksum_orden_y_secreto() -> None:
    cs = event_checksum(["tx1", "APPROVED", "119000"], 1700000000, "evsecret")
    esperado = hashlib.sha256(b"tx1APPROVED1190001700000000evsecret").hexdigest()
    assert cs == esperado


def test_build_y_verify_event_roundtrip() -> None:
    evento = provider_mod.build_signed_event(
        transaction_id="tx-1",
        status="APPROVED",
        referencia="SALE-000001",
        monto_centavos=119000,
        events_secret="evsecret",
    )
    sobre = provider_mod.verify_and_parse_event(evento, events_secret="evsecret")
    assert sobre.transaction_id == "tx-1"
    assert sobre.status.value == "approved"
    assert sobre.referencia == "SALE-000001"
    assert sobre.monto_centavos == 119000
    assert sobre.event_id == "tx-1:approved"


def test_verify_event_firma_invalida() -> None:
    evento = provider_mod.build_signed_event(
        transaction_id="tx-1",
        status="APPROVED",
        referencia="SALE-000001",
        monto_centavos=119000,
        events_secret="evsecret",
    )
    # Manipular el monto sin recalcular el checksum → firma inválida.
    evento["data"]["transaction"]["amount_in_cents"] = 1
    with pytest.raises(InvalidSignature):
        provider_mod.verify_and_parse_event(evento, events_secret="evsecret")


def test_verify_event_secreto_incorrecto() -> None:
    evento = provider_mod.build_signed_event(
        transaction_id="tx-1",
        status="APPROVED",
        referencia="SALE-000001",
        monto_centavos=119000,
        events_secret="evsecret",
    )
    with pytest.raises(InvalidSignature):
        provider_mod.verify_and_parse_event(evento, events_secret="otro-secreto")
