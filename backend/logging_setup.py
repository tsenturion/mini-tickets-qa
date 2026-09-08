"""JSON-логи с request_id и сроком хранения 30 дней для диагностики падений тестов."""

import json
import logging
import re
import time
import uuid
from datetime import datetime, timezone
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

RUN_ID = uuid.uuid4().hex


def clean_logs(directory, now=None):
    """Удалить только старые файлы логов; now позволяет проверить границу срока без ожидания месяца."""
    cutoff = (now if now is not None else time.time()) - 30 * 86400
    for path in Path(directory).glob("*.log*"):
        if path.is_file() and not path.is_symlink() and path.stat().st_mtime < cutoff:
            path.unlink()


class JsonFormatter(logging.Formatter):
    """Сериализовать диагностические поля без сообщения исключения и значений SQL-параметров."""
    def format(self, record):
        """Записать событие и безопасные координаты traceback, не раскрывая пароли из текста ошибки."""
        payload = {"time": datetime.now(timezone.utc).isoformat(), "level": record.levelname,
                   "run_id": RUN_ID, "event": record.getMessage()}
        payload.update(getattr(record, "fields", {}))
        if record.exc_info:
            # Не включаем строку исключения: драйвер может добавить SQL и параметры.
            import traceback
            payload["exception"] = record.exc_info[0].__name__
            payload["trace"] = [{"file": frame.filename, "line": frame.lineno, "function": frame.name}
                                for frame in traceback.extract_tb(record.exc_info[2])]
        return json.dumps(payload, ensure_ascii=False)


def configure(directory, service):
    """Открыть журнал на добавление с суточной ротацией; повторный запуск не затирает старые записи."""
    Path(directory).mkdir(parents=True, exist_ok=True)
    clean_logs(directory)
    logger = logging.getLogger("lab")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)
    handler = TimedRotatingFileHandler(Path(directory) / f"{service}.log", when="midnight", utc=True, backupCount=30, encoding="utf-8")
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    return logger


def request_id(value):
    """Принять ограниченный безопасный идентификатор или создать новый для корреляции UI/API и логов."""
    return value if value and re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", value) else uuid.uuid4().hex
