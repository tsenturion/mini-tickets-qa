-- Адресная очистка того же набора в единой БД monolith/fixed.
-- По умолчанию удаление откатывается; persist=true подтверждает очистку.
\set ON_ERROR_STOP on
\if :{?persist}
\else
    \set persist false
\endif

BEGIN;

-- Показываем цели с теми же условиями, которые будут использованы в DELETE.
SELECT id, ticket_id, author_id, text
FROM comments
WHERE id = :'comment_id'::uuid
  AND ticket_id = :'ticket_id'::uuid
  AND author_id = :'user_id'::uuid;

SELECT id, author_id, title
FROM tickets
WHERE id = :'ticket_id'::uuid
  AND author_id = :'user_id'::uuid
  AND title = 'SQL-набор ' || :'user_id'::uuid::text;

SELECT id, email, role
FROM users
WHERE id = :'user_id'::uuid
  AND email = 'sql-' || :'user_id'::uuid::text || '@example.test'
  AND role = 'user';

-- Сначала зависимые записи: author_id в монолите не имеет ON DELETE CASCADE.
DELETE FROM comments
WHERE id = :'comment_id'::uuid
  AND ticket_id = :'ticket_id'::uuid
  AND author_id = :'user_id'::uuid
RETURNING id, ticket_id, author_id;

DELETE FROM tickets
WHERE id = :'ticket_id'::uuid
  AND author_id = :'user_id'::uuid
  AND title = 'SQL-набор ' || :'user_id'::uuid::text
RETURNING id, author_id, title;

-- Сессии удалятся каскадно по внешнему ключу sessions.user_id -> users.id.
-- Если остались иные ссылки на автора, весь набор удалений откатится при ошибке.
DELETE FROM users
WHERE id = :'user_id'::uuid
  AND email = 'sql-' || :'user_id'::uuid::text || '@example.test'
  AND role = 'user'
RETURNING id, email, role;

\if :persist
    COMMIT;
    \echo 'Адресная очистка подтверждена.'
\else
    ROLLBACK;
    \echo 'Предпросмотр завершён: данные сохранены без изменений.'
\endif
