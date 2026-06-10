"""Configuración central de la aplicación, leída desde variables de entorno."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Base de datos
    database_url: str = "postgresql+psycopg://tendero:tendero@localhost:5436/tendero"

    # Red / CORS
    backend_port: int = 8020
    frontend_origin: str = "http://localhost:3001"

    # Auth (se usa en el Paso 6)
    jwt_secret: str = "cambia-esto-por-un-secreto-de-32-bytes"
    jwt_access_ttl_min: int = 15
    jwt_refresh_ttl_days: int = 7

    # Pagos Wompi (Fase 3). El proveedor por defecto es 'mock' (camino de demo del
    # portafolio). 'real' mapea al API de Wompi pero requiere llaves reales.
    # Las llaves PRIVADAS/secretos viven solo en el servidor (.env), nunca en el repo.
    wompi_provider: str = "mock"  # mock | real
    wompi_public_key: str = "pub_test_demo"
    wompi_private_key: str = ""
    wompi_integrity_secret: str = "integrity_test_secret"
    wompi_events_secret: str = "events_test_secret"

    # Facturación electrónica DIAN vía Proveedor Tecnológico (Fase 4). 'mock' es el
    # camino de demo; 'real' mapea al API del PT (credenciales SOLO en servidor).
    fiscal_provider: str = "mock"  # mock | real
    fiscal_pt_api_url: str = ""
    fiscal_pt_api_key: str = ""
    fiscal_cufe_secret: str = "cufe_demo_secret"


settings = Settings()
