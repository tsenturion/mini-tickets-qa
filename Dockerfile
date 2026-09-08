# Один и тот же lock-файл даёт сопоставимые сборки при локальной проверке и в CI.
FROM node:24.11.1-alpine@sha256:682368d8253e0c3364b803956085c456a612d738bd635926d73fa24db3ce53d7 AS frontend
WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
ARG VITE_DEFECTS=none
# Для UI переключение дефекта требует пересборки; изменение env запущенного контейнера недостаточно.
ENV VITE_DEFECTS=$VITE_DEFECTS
RUN npm run build

FROM python:3.13-slim@sha256:eb43ff125d8d58d7449dcba7d336c23bcac412f526d861db493b9994d8010280 AS backend
# Миграции и seed повторяемы, данные/JSON-логи хранятся в томах, процесс не работает от root.
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt requirements.lock ./
RUN pip install --no-cache-dir -r requirements.txt -c requirements.lock
COPY backend/ backend/
COPY migrations/ migrations/
COPY alembic.ini ./
COPY --from=frontend /build/dist frontend/dist
RUN useradd --uid 10001 --create-home lab && mkdir -p /app/logs && chown -R lab:lab /app
USER lab
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && python -m backend.seed && uvicorn backend.main:app --host 0.0.0.0 --port 8000 --no-access-log"]
