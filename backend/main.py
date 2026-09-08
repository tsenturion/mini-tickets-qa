"""Сборка FastAPI, единые ошибки и наблюдаемость; здесь проверяют путь запроса и отказ зависимостей."""

import asyncio
import time
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException

from backend.config import settings
from backend.database import engine
from backend.logging_setup import clean_logs, configure, request_id
from backend.schemas import ErrorOut

log = configure(settings.log_dir, settings.service)


async def housekeeping():
    """Ежечасно очищать устаревшие журналы работающего сервиса, а не только при следующем запуске."""
    while True:
        await asyncio.sleep(3600)
        clean_logs(settings.log_dir)


@asynccontextmanager
async def lifespan(app):
    """Залогировать запуск/остановку и управлять фоновой очисткой и соединениями БД."""
    log.info("Сервис запущен", extra={"fields": {"service": settings.service}})
    task = asyncio.create_task(housekeeping())
    yield
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task
    engine.dispose()
    log.info("Сервис остановлен")


app = FastAPI(title="Мини-заявки", version="1.0.0", lifespan=lifespan,
    responses={code: {"model": ErrorOut, "description": label} for code, label in {
        401: "Недействующая сессия", 403: "Недостаточно прав", 404: "Ресурс не найден",
        409: "Конфликт состояния", 422: "Ошибка входных данных", 503: "Зависимость недоступна"}.items()})


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Связать ответ и JSON-журнал через X-Request-ID; необработанная ошибка не раскрывает внутренние данные."""
    request.state.request_id = request_id(request.headers.get("X-Request-ID"))
    start = time.monotonic()
    try:
        response = await call_next(request)
    except Exception:
        log.exception("Необработанная ошибка", extra={"fields": {"request_id": request.state.request_id}})
        response = JSONResponse({"error": {"message": "Внутренняя ошибка", "request_id": request.state.request_id}}, status_code=500)
    response.headers["X-Request-ID"] = request.state.request_id
    route = request.scope.get("route")
    log.info("HTTP-запрос", extra={"fields": {"service": settings.service, "request_id": request.state.request_id,
        "method": request.method, "path": getattr(route, "path", "/static"), "status": response.status_code,
        "duration_ms": round((time.monotonic() - start) * 1000, 2)}})
    return response


@app.exception_handler(HTTPException)
async def http_error(request, exc):
    """Привести ожидаемые 401/403/404/409 к общей схеме, сохранив значимые HTTP-заголовки."""
    return JSONResponse({"error": {"message": str(exc.detail), "request_id": request.state.request_id}}, status_code=exc.status_code, headers=exc.headers)


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    """Показать пути ошибочных полей без исходных значений, которые могут содержать пароль."""
    fields = [{"path": list(error["loc"]), "message": error["msg"]} for error in exc.errors()]
    return JSONResponse({"error": {"message": "Некорректные поля", "fields": fields, "request_id": request.state.request_id}}, status_code=422)


@app.exception_handler(SQLAlchemyError)
async def database_error(request, exc):
    """Преобразовать отказ PostgreSQL в 503 и сохранить безопасные детали в серверном журнале."""
    log.error("Ошибка PostgreSQL", exc_info=exc, extra={"fields": {"request_id": request.state.request_id}})
    return JSONResponse({"error": {"message": "База данных недоступна", "request_id": request.state.request_id}}, status_code=503)


@app.get("/health/ready", include_in_schema=False)
def ready():
    """Подтвердить доступность БД и миграции, чтобы CI не начинал тесты на недоготовленном приложении."""
    with engine.connect() as connection:
        connection.execute(text("SELECT version_num FROM alembic_version"))
    return {"status": "ready", "service": settings.service}


if settings.service in {"all", "identity"}:
    from backend.auth import router as auth_router
    app.include_router(auth_router)
if settings.service in {"all", "tickets"}:
    from backend.tickets import router as ticket_router
    app.include_router(ticket_router)

if settings.service == "all" and Path(settings.frontend_dir).is_dir():
    app.mount("/", StaticFiles(directory=settings.frontend_dir, html=True), name="frontend")
