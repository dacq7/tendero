"""Firmas Wompi (SHA256). Funciones PURAS, idénticas para mock y real.

- Firma de integridad de transacción: SHA256(referencia + monto + moneda + secreto).
- Checksum de evento de webhook: SHA256(valores de las propiedades firmadas, en
  orden + timestamp + secreto de eventos). Es el esquema real de Wompi.
"""

import hashlib


def integrity_signature(referencia: str, monto_centavos: int, moneda: str, secret: str) -> str:
    raw = f"{referencia}{monto_centavos}{moneda}{secret}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def event_checksum(values: list[str], timestamp: int | str, secret: str) -> str:
    raw = "".join(str(v) for v in values) + str(timestamp) + secret
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _dotted(payload: dict, path: str):
    """Lee 'data.transaction.id' del payload anidado."""
    node = payload
    for key in path.split("."):
        node = node[key]
    return node
