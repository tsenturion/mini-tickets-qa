"""Регрессия ошибки mount, которую нельзя объявлять пустой тестовой работой."""
import errno

import pytest

from grader import entrypoint


def test_mount_probe_keeps_source_and_cleans_its_temporary_file(tmp_path):
    """Проверка читает каталог, не меняет работу и не оставляет мусор в отчётах."""
    source, results = tmp_path / "source", tmp_path / "results"
    source.mkdir()
    results.mkdir()
    marker = source / "test_sample.py"
    marker.write_text("assert True")
    entrypoint.check_mounts(source, results)
    assert marker.read_text() == "assert True"
    assert list(results.iterdir()) == []


def test_ready_mounts_delegate_to_pytest_and_preserve_exit_code(monkeypatch):
    """После проверки каталогов сохранить изоляцию Pytest, аргументы и код результата."""
    calls = []

    def ready_mounts():
        """Зафиксировать проверку каталогов до запуска присланных тестов."""
        calls.append("mounts")

    def pytest_run(arguments, **options):
        """Проверить контракт запуска без загрузки внешних плагинов."""
        calls.append("pytest")
        assert arguments == [entrypoint.sys.executable, "-m", "pytest",
                             *entrypoint.PYTEST_OPTIONS, "tests", "-m", "api"]
        assert options == {"cwd": "/submission"}
        return 1

    monkeypatch.setattr(entrypoint, "check_mounts", ready_mounts)
    monkeypatch.setattr(entrypoint.subprocess, "call", pytest_run)
    assert entrypoint.main(["tests", "-m", "api"]) == 1
    assert calls == ["mounts", "pytest"]


@pytest.mark.parametrize("code", [errno.EIO, errno.EACCES, errno.ENOENT])
def test_mount_failure_stops_before_loading_student_code(monkeypatch, capsys, code):
    """EIO, ACL и отсутствующий mount дают служебный код 78 до запуска Pytest."""
    def broken_mounts():
        """Воспроизвести отказ ОС независимо от прав тестовой машины."""
        raise OSError(code, "Ошибка каталога")

    def forbidden_test_run(*args, **kwargs):
        """Любая попытка загрузить работу после отказа mount является регрессией."""
        pytest.fail("Pytest не должен запускаться")

    monkeypatch.setattr(entrypoint, "check_mounts", broken_mounts)
    monkeypatch.setattr(entrypoint.subprocess, "call", forbidden_test_run)
    assert entrypoint.main(["tests"]) == 78
    assert '"event": "grader_mount_error"' in capsys.readouterr().err
