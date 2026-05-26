from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    APP_NAME: str = "Private RFP Tool"
    AI_MODE: str = "private"
    DATABASE_URL: str = f"sqlite:///{(BACKEND_ROOT / 'private_rfp.db').as_posix()}"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_CHAT_MODEL: str = "llama3.2:3b"
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text"
    UPLOAD_DIR: str = "storage/uploads"
    MAX_UPLOAD_MB: int = Field(default=50, ge=1)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    def validate_private_mode(self) -> None:
        if self.AI_MODE != "private":
            raise ValueError("Only AI_MODE=private is allowed for this MVP.")


def _normalize_sqlite_url(url: str) -> str:
    if not url.startswith("sqlite:///"):
        return url

    database_path = url[len("sqlite:///") :]
    if not database_path:
        return url

    if database_path.startswith("/") or (len(database_path) >= 2 and database_path[1] == ":"):
        return url

    resolved = (BACKEND_ROOT / database_path).resolve()
    return f"sqlite:///{resolved.as_posix()}"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.DATABASE_URL = _normalize_sqlite_url(settings.DATABASE_URL)
    settings.validate_private_mode()
    return settings


settings = get_settings()
