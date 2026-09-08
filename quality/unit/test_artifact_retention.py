"""Проверки адресной очистки 30-дневных диагностических артефактов."""

import os
import time

import pytest

from scripts.clean_artifacts import cleanup


def test_only_expired_files_are_removed(tmp_path):
    """Искусственно состарить файлы, сохранив свежие и соседние данные; запретить опасный корневой путь."""
    directory = tmp_path / "artifacts"
    directory.mkdir()
    old = directory / "old.json"
    new = directory / "current.json"
    old.write_text("{}")
    new.write_text("{}")
    os.utime(old, (time.time() - 31 * 86400,) * 2)
    assert cleanup(directory) == 1
    assert new.exists() and not old.exists()
    with pytest.raises(ValueError):
        cleanup(tmp_path)
