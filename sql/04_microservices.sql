-- Подключение к базе tickets: межбазовых JOIN с users нет.
SELECT t.title, count(c.id) AS comments FROM tickets t LEFT JOIN comments c ON c.ticket_id = t.id GROUP BY t.id, t.title;
SELECT id, author_id FROM tickets ORDER BY created_at DESC, id DESC;
-- Идентификаторы авторов проверяются через сервис пользователей и разрешённые API-сценарии.

