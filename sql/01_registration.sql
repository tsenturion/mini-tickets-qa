-- Запускать только в личной учебной БД монолита или клиент-серверного варианта.
-- Хеш копируется из учебной записи; пароль такой же, как у исходного аккаунта.
BEGIN;
INSERT INTO users (id, email, password_hash, role)
SELECT '00000000-0000-0000-0000-000000009001', 'sql-student@example.test', password_hash, 'user'
FROM users WHERE email = 'anna@example.test';
SELECT id, email, role FROM users WHERE email = 'sql-student@example.test';
ROLLBACK;
-- Повторите с COMMIT и сравните видимость записи из другого соединения.

