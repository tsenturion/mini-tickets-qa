-- Проверка точного набора: передайте те же user_id, ticket_id, comment_id.
-- Пароли, хеши и значения сессий не выводятся.
\set ON_ERROR_STOP on

SELECT current_database() AS database_name, current_user AS database_role;

SELECT id, email, role
FROM users
WHERE id = :'user_id'::uuid;

SELECT id, author_id, title, priority, status, created_at
FROM tickets
WHERE id = :'ticket_id'::uuid;

SELECT id, ticket_id, author_id, text, created_at
FROM comments
WHERE id = :'comment_id'::uuid;

-- Счётчики читают каждый UUID независимо от дополнительных условий очистки.
-- Поэтому неверный marker в DELETE не сможет скрыть оставшуюся запись.
SELECT
    (SELECT count(*) FROM users WHERE id = :'user_id'::uuid) AS users_count,
    (SELECT count(*) FROM tickets WHERE id = :'ticket_id'::uuid) AS tickets_count,
    (SELECT count(*) FROM comments WHERE id = :'comment_id'::uuid) AS comments_count,
    (SELECT count(*) FROM sessions WHERE user_id = :'user_id'::uuid) AS sessions_count;
