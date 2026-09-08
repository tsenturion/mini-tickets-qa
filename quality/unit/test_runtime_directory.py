"""Регрессия ошибки ACL Windows без изменения прав системного временного каталога."""
import pytest

from scripts.runtime_directory import runtime_directory


def test_unique_directories_and_targeted_cleanup(tmp_path):
    """Два параллельных прогона не делят данные, а очистка не удаляет соседа."""
    sentinel = tmp_path / "оставить.txt"
    sentinel.write_text("чужие данные", encoding="utf-8")
    with runtime_directory("first", tmp_path) as first:
        with runtime_directory("second", tmp_path) as second:
            assert first != second
            assert first.parent == second.parent == tmp_path
        assert not second.exists() and first.exists()
    assert not first.exists() and sentinel.exists()


def test_cleanup_after_exception(tmp_path):
    """Ошибка тестирования освобождает собственный временный каталог."""
    with pytest.raises(RuntimeError, match="сбой"):
        with runtime_directory("failure", tmp_path) as directory:
            raise RuntimeError("сбой")
    assert not directory.exists()


def test_directory_inherits_acl_instead_of_private_mode(tmp_path, monkeypatch):
    """Создание каталога не использует 0o700, мешающий bind-mount Docker Desktop."""
    from pathlib import Path
    original = Path.mkdir
    modes = []

    def record(self, mode=0o777, **kwargs):
        """Записать режим без подмены фактического создания каталога."""
        modes.append(mode)
        return original(self, mode=mode, **kwargs)

    monkeypatch.setattr(Path, "mkdir", record)
    with runtime_directory("acl", tmp_path):
        assert 0o700 not in modes
