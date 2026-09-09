from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    FRONTEND_VALIDATION_URL: str = "http://localhost:5173/validar"
    ALLOWED_ORIGINS: str = "http://localhost:5173"

    # Propiedades para CORS
    @property
    def cors_origins(self) -> List[str]:
        # Divide por comas y limpia espacios, o usa wildcard en dev
        if not self.ALLOWED_ORIGINS:
            return ["*"]
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


settings = Settings()
