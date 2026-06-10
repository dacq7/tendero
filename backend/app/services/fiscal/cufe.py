"""CUFE SIMULADO (demo). Función PURA, determinista.

El CUFE real de la DIAN es un SHA384 sobre campos fiscales en un orden definido +
clave técnica. Aquí simulamos un SHA256 determinista sobre los campos fiscales +
un secreto de demo: reemitir la misma factura da el MISMO CUFE (idempotencia).
NO tiene validez fiscal; es solo demostración de portafolio.
"""

import hashlib


def compute_cufe(
    *,
    numero_fiscal_completo: str,
    fecha: str,
    subtotal_centavos: int,
    iva_total_centavos: int,
    total_centavos: int,
    rut_nit: str,
    numero_resolucion: str,
    secret: str,
) -> str:
    raw = (
        f"{numero_fiscal_completo}{fecha}{subtotal_centavos}{iva_total_centavos}"
        f"{total_centavos}{rut_nit}{numero_resolucion}{secret}"
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
