-- Изменения адресованы только известной учебной записи этого упражнения.
BEGIN;
INSERT INTO tickets(id, author_id, title, priority, status, created_at)
VALUES ('00000000-0000-0000-0000-000000009002','00000000-0000-0000-0000-000000000001','SQL-проверка','normal','new',now());
UPDATE tickets SET priority = 'high' WHERE id = '00000000-0000-0000-0000-000000009002';
SELECT title, priority FROM tickets WHERE id = '00000000-0000-0000-0000-000000009002';
DELETE FROM tickets WHERE id = '00000000-0000-0000-0000-000000009002';
COMMIT;

