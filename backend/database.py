"""Подключение к настоящей PostgreSQL для проверки транзакций и сохранения данных."""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.config import settings

# pre_ping позволяет восстановиться после перезапуска PostgreSQL; параметры SQL
# скрыты, чтобы пароль/тестовый текст не попал в диагностику исключения.
engine = create_engine(settings.database_url, pool_pre_ping=True, hide_parameters=True)


def database():
    """Выдать сессию БД на запрос и закрыть её после обработки; commit выполняет конкретная операция."""
    with Session(engine) as session:
        yield session
