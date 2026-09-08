"""Проверки хранения, корреляции и редактирования чувствительных данных в логах."""

import json
import logging
import os
import time

from backend.logging_setup import JsonFormatter, clean_logs, configure, request_id


def test_retention_and_restart(tmp_path):
    """Подтвердить очистку старых файлов и добавление, а не перезапись журнала при повторной настройке."""
    old = tmp_path / "all.log.2000-01-01"
    old.write_text("старый", encoding="utf-8")
    os.utime(old, (time.time() - 31 * 86400,) * 2)
    recent = tmp_path / "all.log.2026-01-01"
    recent.write_text("сохранить", encoding="utf-8")
    configure(tmp_path, "all").info("первый запуск")
    configure(tmp_path, "all").info("второй запуск")
    clean_logs(tmp_path)
    assert not old.exists()
    assert recent.exists()
    text = (tmp_path / "all.log").read_text(encoding="utf-8")
    assert "первый запуск" in text and "второй запуск" in text


def test_request_id_is_bounded():
    """Отвергнуть перевод строки и слишком длинный request_id, сохранив корректное значение."""
    assert request_id("abc-12") == "abc-12"
    assert "\n" not in request_id("bad\ninput")
    assert len(request_id("x" * 1000)) == 32


def test_exception_does_not_expose_message():
    """Создать исключение с тестовым секретом и доказать, что его текст не попал в JSON."""
    try:
        raise ValueError("secret-password")
    except ValueError:
        import sys
        record = logging.LogRecord("lab", 40, "test", 1, "ошибка", (), sys.exc_info())
    payload = json.loads(JsonFormatter().format(record))
    assert "secret-password" not in json.dumps(payload)
    assert payload["exception"] == "ValueError"
