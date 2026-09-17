# Tag сохраняет читаемую версию, а digest фиксирует точные байты базового образа:
# повторная сборка не получит незаметно изменённый Node.js при том же имени tag.
FROM node:24.11.1-alpine@sha256:682368d8253e0c3364b803956085c456a612d738bd635926d73fa24db3ce53d7 AS frontend
WORKDIR /build
# Манифесты копируются до исходников, чтобы слой npm переиспользовался при
# изменении Vue-кода. npm ci проверяет соответствие package-lock и не обновляет
# дерево зависимостей неявно во время CI-сборки.
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
ARG VITE_DEFECTS=none
# Для UI переключение дефекта требует пересборки; изменение env запущенного контейнера недостаточно.
ENV VITE_DEFECTS=$VITE_DEFECTS
RUN npm run build

# Python-основа также закреплена digest; frontend-инструменты и node_modules не
# переходят в runtime-образ благодаря отдельной стадии backend.
FROM python:3.13-slim@sha256:eb43ff125d8d58d7449dcba7d336c23bcac412f526d861db493b9994d8010280 AS backend
# Миграции и seed повторяемы, данные/JSON-логи хранятся в томах, процесс не работает от root.
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
# requirements.txt задаёт прямые зависимости, constraints lock — разрешённые
# транзитивные версии. --no-cache-dir не переносит установочный кеш pip в слой
# приложения и уменьшает поверхность runtime-образа.
COPY requirements.txt requirements.lock ./
RUN pip install --no-cache-dir -r requirements.txt -c requirements.lock
COPY backend/ backend/
COPY migrations/ migrations/
COPY alembic.ini ./
# Из frontend-стадии переносится только собранная статика: исходники, npm и
# node_modules не увеличивают backend-образ и не становятся runtime-инструментами.
COPY --from=frontend /build/dist frontend/dist
# Фиксированный непривилегированный UID делает владельца файлов предсказуемым.
# chown выполняется до USER, чтобы процесс мог писать JSON-логи в подключённый
# каталог /app/logs без полномочий root.
RUN useradd --uid 10001 --create-home lab && mkdir -p /app/logs && chown -R lab:lab /app
USER lab
EXPOSE 8000
# Цепочка запуска fail-fast: при ошибке миграции или seed Uvicorn не стартует,
# контейнер завершается ненулевым кодом, а healthcheck не маскирует причину.
# Миграции повторяются при старте контейнера, долговечные данные живут в volume.
CMD ["sh", "-c", "alembic upgrade head && python -m backend.seed && uvicorn backend.main:app --host 0.0.0.0 --port 8000 --no-access-log"]
