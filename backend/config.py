import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "postgresql+psycopg://lab:lab@localhost:5432/lab")
    service: str = os.getenv("SERVICE", "all")
    identity_url: str = os.getenv("IDENTITY_URL", "http://identity:8000")
    log_dir: str = os.getenv("LOG_DIR", "logs")
    frontend_dir: str = os.getenv("FRONTEND_DIR", "frontend/dist")
    session_seconds: int = int(os.getenv("SESSION_SECONDS", "3600"))


settings = Settings()

