"""Запуск миграций Alembic в транзакции выбранной PostgreSQL; create_all не подменяет проверку схемы."""

from alembic import context
from sqlalchemy import create_engine

from backend.config import settings

with create_engine(settings.database_url, hide_parameters=True).connect() as connection:
    context.configure(connection=connection)
    with context.begin_transaction():
        context.run_migrations()
