"""Проверка ранней диагностики отсутствующего Docker/образа вместо ложного провала студента."""

import pytest
import json
from subprocess import CompletedProcess

from grader import run


def test_missing_image_has_preparation_instruction(monkeypatch):
    """Убедиться, что отсутствие образа даёт конкретную команду подготовки до создания стендов."""
    calls = []

    def command(args, **kwargs):
        """Подменить только внешнюю команду для воспроизведения отказа без остановки настоящего Docker."""
        calls.append(args)
        if args[1] == "image":
            raise RuntimeError("образ отсутствует")
        return "29"

    monkeypatch.setattr(run, "command", command)
    with pytest.raises(RuntimeError, match="Prepare-Lab.ps1"):
        run.require_runtime()
    assert len(calls) == 2


def test_unavailable_docker_is_not_a_student_failure(monkeypatch):
    """Сохранить причину недоступности Docker как ошибку среды, а не найденный дефект."""
    def command(*args, **kwargs):
        """Подменить только внешнюю команду для воспроизведения отказа без остановки настоящего Docker."""
        raise RuntimeError("Docker недоступен")

    monkeypatch.setattr(run, "command", command)
    with pytest.raises(RuntimeError, match="Docker недоступен"):
        run.require_runtime()


@pytest.mark.parametrize("code", [78, 125, 126, 127])
def test_docker_launch_error_is_infrastructure(monkeypatch, tmp_path, code):
    """Отказ запуска контейнера не равен AssertionError и не уменьшает оценку студента."""
    def failed_container(*args, **kwargs):
        """Воспроизвести коды Docker без настоящего контейнера и сохранить сообщение ACL."""
        return CompletedProcess(args, code, "", "Access is denied")

    monkeypatch.setattr(run.subprocess, "run", failed_container)
    output = tmp_path / "results"
    result = run.run_submission(tmp_path, output, "tests", "app:8000", "test-runner")
    assert result["infrastructure_error"] is True
    assert result["exit_code"] == code
    assert "Access is denied" in (output / "runner.log").read_text()


def test_failed_baseline_stops_before_mutants(monkeypatch, tmp_path):
    """Первый отказ среды останавливает длинную матрицу, но оставляет машиночитаемый отчёт."""
    refs = tmp_path / "refs.json"
    refs.write_text("{}")
    calls = []

    def scenario(architecture, state, *args, **kwargs):
        """Зафиксировать обращение к стенду и вернуть недоступную инфраструктуру."""
        calls.append((architecture, state))
        return {"infrastructure_error": True, "reason": "Access is denied"}

    def no_external_command(*args, **kwargs):
        """Не запускать Docker, Git и очистку настоящих отчётов в модульном тесте."""
        return "test-commit"

    monkeypatch.setattr(run, "scenario", scenario)
    for name in ["require_runtime", "snapshot", "command", "cleanup"]:
        monkeypatch.setattr(run, name, no_external_command)
    monkeypatch.setattr(run.sys, "argv", ["grader/run.py", "--submission", str(tmp_path),
        "--output", str(tmp_path / "report"), "--refs", str(refs), "--full"])
    assert run.main() == 2
    assert calls == [("monolith", "fixed")]
    assert json.loads((tmp_path / "report/grade.json").read_text())["status"] == "infrastructure_error"
