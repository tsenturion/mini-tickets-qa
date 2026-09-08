"""Интеграционные проверки настоящей PostgreSQL: HTTP-запись, каскад и восстановление транзакции."""

import os
import uuid

import psycopg
import pytest

pytestmark = pytest.mark.sql


@pytest.fixture
def connection():
    """Открыть соединение личной тестовой БД и откатить незавершённую транзакцию после теста."""
    url = os.environ["SQL_DATABASE_URL"]
    with psycopg.connect(url) as connection:
        yield connection
        connection.rollback()


def test_post_creates_real_row_and_delete_cascades(api, connection):
    """Сопоставить POST и SELECT, затем доказать удаление комментария каскадом, а не только исчезновение из UI."""
    ticket = api.create()
    response = api.request("POST", f"/tickets/{ticket['id']}/comments", json={"text": "Проверка связи"})
    assert response.status_code == 201
    row = connection.execute("SELECT title, author_id FROM tickets WHERE id = %s", (ticket["id"],)).fetchone()
    assert row == (ticket["title"], uuid.UUID(api.user["id"]))
    assert api.request("DELETE", f"/tickets/{ticket['id']}").status_code == 204
    assert connection.execute("SELECT count(*) FROM comments WHERE ticket_id = %s", (ticket["id"],)).fetchone()[0] == 0


def test_foreign_key_and_rollback(connection):
    """Проверить отказ FK и обязательный ROLLBACK перед последующим запросом."""
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        connection.execute("INSERT INTO comments(id,ticket_id,author_id,text,created_at) VALUES (%s,%s,%s,%s,now())",
            (uuid.uuid4(), uuid.uuid4(), uuid.UUID(int=1), "Несуществующая заявка"))
    connection.rollback()
    assert connection.execute("SELECT 1").fetchone() == (1,)
