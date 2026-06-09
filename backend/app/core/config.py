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


settings = Settings()
