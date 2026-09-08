"""Таблицы пользователей и сессий, которыми владеет сервис identity; основа SQL-практики."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class IdentityBase(DeclarativeBase):
    """Отдельные ORM-метаданные identity: сервис заявок не должен читать эти таблицы напрямую."""
    pass


class User(IdentityBase):
    """Учётная запись с уникальным email, Argon2-хешем и ролью; хеш не входит в ответ API."""
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="user")


class LoginSession(IdentityBase):
    """Отзываемая сессия: в БД хранится хеш токена и UTC-срок действия, а не Bearer-секрет."""
    __tablename__ = "sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


def utcnow():
    """Вернуть timezone-aware UTC, чтобы сравнение сроков не зависело от часового пояса стенда."""
    return datetime.now(timezone.utc)
