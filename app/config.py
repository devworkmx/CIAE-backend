from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    FRONTEND_VALIDATION_URL: str = "http://localhost:5173/validar"
    # En producción, define ALLOWED_ORIGINS en el .env con el/los dominio(s)
    # exactos del frontend, separados por comas si hay más de uno.
    # Ejemplo: ALLOWED_ORIGINS=https://certificados.miempresa.com
    ALLOWED_ORIGINS: str = "http://localhost:5173"

    # Propiedades para CORS
    @property
    def cors_origins(self) -> List[str]:
        # Divide por comas y limpia espacios. NUNCA usar "*" con
        # allow_credentials=True: el navegador lo rechaza y además
        # equivaldría a aceptar peticiones autenticadas desde cualquier sitio.
        if not self.ALLOWED_ORIGINS:
            return []
        return [origen.strip() for origen in self.ALLOWED_ORIGINS.split(",") if origen.strip()]

    # Compatibilidad con database.py y security.py
    @property
    def database_url(self) -> str:
        return self.DATABASE_URL

    @property
    def secret_key(self) -> str:
        return self.SECRET_KEY

    @property
    def algorithm(self) -> str:
        return self.ALGORITHM

    @property
    def access_token_expire_minutes(self) -> int:
        return self.ACCESS_TOKEN_EXPIRE_MINUTES

    @property
    def frontend_validation_url(self) -> str:
        return self.FRONTEND_VALIDATION_URL

    @property
    def allowed_origins(self) -> str:
        return self.ALLOWED_ORIGINS

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    RESEND_API_KEY: str = ""
    RESEND_FROM_EMAIL: str = "onboarding@resend.dev"
    FRONTEND_URL: str = "http://localhost:5173"  # O el puerto donde corra tu React


settings = Settings()
