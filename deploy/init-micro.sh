#!/bin/sh
# Выполняется PostgreSQL только при первом создании тома; две БД имеют разные роли.
# REVOKE проверяется отдельным негативным SQL-тестом: знание имени БД не даёт доступа.
set -eu
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<'SQL'
CREATE ROLE identity LOGIN PASSWORD 'identity-local-only';
CREATE ROLE tickets LOGIN PASSWORD 'tickets-local-only';
CREATE DATABASE identity OWNER identity;
CREATE DATABASE tickets OWNER tickets;
REVOKE CONNECT ON DATABASE identity FROM PUBLIC;
REVOKE CONNECT ON DATABASE tickets FROM PUBLIC;
GRANT CONNECT ON DATABASE identity TO identity;
GRANT CONNECT ON DATABASE tickets TO tickets;
SQL
