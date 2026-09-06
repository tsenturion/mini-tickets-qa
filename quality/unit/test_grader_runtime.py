import pytest

from grader import run


def test_missing_image_has_preparation_instruction(monkeypatch):
    calls = []

    def command(args, **kwargs):
        calls.append(args)
        if args[1] == "image":
            raise RuntimeError("образ отсутствует")
        return "29"

    monkeypatch.setattr(run, "command", command)
    with pytest.raises(RuntimeError, match="Prepare-Lab.ps1"):
        run.require_runtime()
    assert len(calls) == 2


def test_unavailable_docker_is_not_a_student_failure(monkeypatch):
    def command(*args, **kwargs):
        raise RuntimeError("Docker недоступен")

    monkeypatch.setattr(run, "command", command)
    with pytest.raises(RuntimeError, match="Docker недоступен"):
        run.require_runtime()
