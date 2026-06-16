"""
Configuración del backend Conecta 4.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuración de la aplicación."""

    # API
    app_name: str = "Conecta 4 API"
    app_version: str = "0.1.0"
    debug: bool = True

    # CORS
    cors_origins: list[str] = [
        "http://localhost:4200",
        "http://127.0.0.1:4200",
    ]

    # Servidor
    host: str = "0.0.0.0"
    port: int = 8000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()