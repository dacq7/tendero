"""Configuración central de la aplicación, leída desde variables de entorno.

Endurecimiento (Fase 6 B.1): los secretos NO tienen valor por defecto en código.
Son campos REQUERIDOS de pydantic-settings: si faltan en el entorno (o en `.env`),
la aplicación falla RUIDOSAMENTE al arrancar con un `ValidationError` claro, en vez
de operar en silencio con credenciales conocidas. Los valores de prueba del modo
`mock` (camino de demo del portafolio) viven en `.env`/`.env.example`, nunca aquí.
"""

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Valores de PRUEBA del modo mock (los de `.env.example`). En producción son una
# trampa: con ellos cualquiera firma un webhook válido. La guarda de abajo prohíbe
# arrancar en producción con cualquiera de estos.
_DEMO_SECRETS = frozenset(
    {
        "integrity_test_secret",
        "events_test_secret",
        "cufe_demo_secret",
        "cambia-esto-por-un-secreto-de-32-bytes",
        "pub_test_demo",
        # JWT de la suite e2e (frontend/e2e/env.ts): de prueba, jamás de producción.
        "e2e_jwt_secret_no_real_solo_para_pruebas",
    }
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Entorno de despliegue: 'development' | 'test' | 'production'. Gobierna el
    # endurecimiento sensible al entorno (HSTS, ocultar trazas, guarda anti-prod).
    app_env: str = "development"

    # Base de datos (REQUERIDO — sin default: arrancar sin él falla ruidosamente).
    database_url: str

    # Red / CORS
    backend_port: int = 8020
    frontend_origin: str = "http://localhost:3001"

    # Auth. `jwt_secret` es REQUERIDO (sin default): es la raíz de confianza de toda
    # la sesión; un default conocido permitiría forjar tokens.
    jwt_secret: str
    jwt_access_ttl_min: int = 15
    jwt_refresh_ttl_days: int = 7

    # Pagos Wompi (Fase 3). El proveedor por defecto es 'mock' (camino de demo del
    # portafolio). 'real' mapea al API de Wompi pero requiere llaves reales.
    # Las llaves PRIVADAS/secretos viven solo en el servidor (.env), nunca en el repo.
    # `wompi_public_key` es PÚBLICA por diseño (no secreta) → conserva un default.
    # Los secretos de firma son REQUERIDOS: el mock los usa para firmar de verdad.
    wompi_provider: str = "mock"  # mock | real
    wompi_public_key: str = "pub_test_demo"
    wompi_private_key: str = ""  # solo modo 'real' (validado en RealWompiProvider)
    wompi_integrity_secret: str
    wompi_events_secret: str

    # Facturación electrónica DIAN vía Proveedor Tecnológico (Fase 4). 'mock' es el
    # camino de demo; 'real' mapea al API del PT (credenciales SOLO en servidor).
    fiscal_provider: str = "mock"  # mock | real
    fiscal_pt_api_url: str = ""  # solo modo 'real' (validado en RealFiscalProvider)
    fiscal_pt_api_key: str = ""  # solo modo 'real'
    fiscal_cufe_secret: str  # REQUERIDO: el mock firma el CUFE simulado con él

    @model_validator(mode="after")
    def _reject_demo_secrets_in_production(self) -> "Settings":
        """En producción, ningún secreto puede ser un placeholder de demo conocido."""
        if self.app_env != "production":
            return self
        ofensores = [
            nombre
            for nombre, valor in {
                "JWT_SECRET": self.jwt_secret,
                "WOMPI_INTEGRITY_SECRET": self.wompi_integrity_secret,
                "WOMPI_EVENTS_SECRET": self.wompi_events_secret,
                "FISCAL_CUFE_SECRET": self.fiscal_cufe_secret,
            }.items()
            if valor in _DEMO_SECRETS
        ]
        if ofensores:
            raise ValueError(
                "En producción no se permiten secretos de demo. Reemplaza: "
                + ", ".join(sorted(ofensores))
            )
        return self


settings = Settings()
