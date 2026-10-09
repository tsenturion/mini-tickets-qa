-- Подготовка связанного набора в единой БД monolith/fixed.
-- psql получает user_id, ticket_id, comment_id; persist=true подтверждает запись.
-- По умолчанию набор виден внутри скрипта, затем полностью откатывается.
\set ON_ERROR_STOP on
\if :{?persist}
\else
    \set persist false
\endif

BEGIN;

-- Argon2-хеш копируется внутри БД, но не попадает в вывод скрипта.
-- Новый пользователь войдёт с учебным паролем исходной записи Anna.
INSERT INTO users (id, email, password_hash, role)
SELECT :'user_id'::uuid,
       'sql-' || :'user_id'::uuid::text || '@example.test',
       password_hash,
       'user'
FROM users
WHERE email = 'anna@example.test'
RETURNING id, email, role;

-- UUID и значения по умолчанию задаём явно: defaults ORM не действуют в SQL.
INSERT INTO tickets (id, author_id, title, priority, status, created_at)
VALUES (:'ticket_id'::uuid, :'user_id'::uuid,
        'SQL-набор ' || :'user_id'::uuid::text, 'high', 'new', now())
RETURNING id, author_id, title, priority, status, created_at;

INSERT INTO comments (id, ticket_id, author_id, text, created_at)
VALUES (:'comment_id'::uuid, :'ticket_id'::uuid, :'user_id'::uuid,
        'Комментарий из SQL-набора', now())
RETURNING id, ticket_id, author_id, text, created_at;

\if :persist
    COMMIT;
    \echo 'Тестовый набор сохранён.'
\else
    ROLLBACK;
    \echo 'Предпросмотр завершён: тестовый набор не сохранён.'
\endif
