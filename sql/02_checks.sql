-- Связь пользователей с заявками; пользователи без заявок сохраняются в LEFT JOIN.
SELECT u.email, t.id, t.title FROM users u INNER JOIN tickets t ON t.author_id = u.id;
SELECT u.email, count(t.id) AS ticket_count FROM users u LEFT JOIN tickets t ON t.author_id = u.id
GROUP BY u.id, u.email ORDER BY ticket_count DESC, u.email;
SELECT t.title, c.text FROM comments c RIGHT JOIN tickets t ON t.id = c.ticket_id ORDER BY t.created_at, t.id;
-- Автор комментария может отличаться от автора заявки.
SELECT t.title, owner.email AS owner, actor.email AS commenter, c.text
FROM comments c JOIN tickets t ON t.id = c.ticket_id
JOIN users owner ON owner.id = t.author_id JOIN users actor ON actor.id = c.author_id;
SELECT status, priority, count(*) FROM tickets WHERE created_at >= '2026-01-01' GROUP BY status, priority;
-- Этот запрос должен вернуть ноль строк.
SELECT c.id FROM comments c LEFT JOIN tickets t ON t.id = c.ticket_id WHERE t.id IS NULL;
-- Проверка конкретного POST: в psql задайте переменную через \set ticket_id 'полученный-uuid'.
-- SELECT id, title, priority, status, author_id FROM tickets WHERE id = :'ticket_id';

