"""Детерминированные учебные записи для ручных, API- и SQL-проверок без реальных персональных данных."""

import uuid
from datetime import datetime, timezone

from argon2 import PasswordHasher
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import engine
from backend.logging_setup import configure

USERS = [(1, "anna@example.test", "user"), (2, "boris@example.test", "user"), (3, "operator@example.test", "operator")]


def seed():
    """Идемпотентно добавить отсутствующие начальные записи; повторный запуск не сбрасывает изменения студентов."""
    log = configure(settings.log_dir, settings.service)
    with Session(engine) as db:
        if settings.service in {"all", "identity"}:
            from backend.models_identity import User
            hasher = PasswordHasher()
            for number, email, role in USERS:
                if not db.get(User, uuid.UUID(int=number)):
                    db.add(User(id=uuid.UUID(int=number), email=email, role=role, password_hash=hasher.hash("LabPassword1!")))
            db.commit()
        if settings.service in {"all", "tickets"}:
            from backend.models_tickets import Comment, Ticket
            for index, status in enumerate(["new", "active", "closed", "new"], 10):
                if not db.get(Ticket, uuid.UUID(int=index)):
                    db.add(Ticket(id=uuid.UUID(int=index), author_id=uuid.UUID(int=1 if index < 13 else 2), title=f"Учебная заявка {index}",
                        priority="normal", status=status, created_at=datetime(2026, 1, index, tzinfo=timezone.utc)))
            db.commit()
            if not db.get(Comment, uuid.UUID(int=100)):
                db.add(Comment(id=uuid.UUID(int=100), ticket_id=uuid.UUID(int=10), author_id=uuid.UUID(int=3),
                    text="Проверяем сохранение автора", created_at=datetime(2026, 1, 10, tzinfo=timezone.utc)))
            db.commit()
    log.info("Учебные данные подготовлены")


if __name__ == "__main__":
    seed()
