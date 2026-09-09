"""Проверки передачи GitLab job token без раскрытия в адресах клонирования."""
import base64
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("ci_grade", Path(__file__).resolve().parents[2] / "student-template/ci_grade.py")
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


def test_job_token_uses_temporary_git_environment():
    """Данные авторизации остаются только в отдельной среде Git с запретом редиректов."""
    original = {"CI_JOB_TOKEN": "example-token", "CI_SERVER_URL": "http://localhost:8929", "GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "core.longpaths", "GIT_CONFIG_VALUE_0": "true"}
    result = adapter.clone_environment("http://localhost:8929/course/product.git", original)
    assert result["GIT_CONFIG_COUNT"] == "3"
    assert result["GIT_CONFIG_KEY_0"] == "core.longpaths"
    assert result["GIT_CONFIG_KEY_1"] == "http.http://localhost:8929/.extraHeader"
    assert base64.b64decode(result["GIT_CONFIG_VALUE_1"].split()[-1]).decode() == "gitlab-ci-token:example-token"
    assert result["GIT_CONFIG_KEY_2"] == "http.followRedirects"
    assert result["GIT_CONFIG_VALUE_2"] == "false"
    assert original["GIT_CONFIG_COUNT"] == "1"


@pytest.mark.parametrize("url,server", [
    ("https://foreign.example/product.git", "https://gitlab.example"),
    ("http://gitlab.example/product.git", "http://gitlab.example"),
    ("http://localhost:8930/product.git", "http://localhost:8929"),
    ("http://user:password@localhost:8929/product.git", "http://localhost:8929"),
])
def test_job_token_rejects_foreign_or_unsafe_origin(url, server):
    """Запретить отправку секрета другому серверу и незащищённому удалённому HTTP."""
    with pytest.raises(ValueError):
        adapter.clone_environment(url, {"CI_JOB_TOKEN": "example-token", "CI_SERVER_URL": server})


def test_public_clone_needs_no_token():
    """Ручной запуск без job token использует обычную авторизацию Git."""
    assert adapter.clone_environment("https://example.test/repo.git", {}) == {"GIT_TERMINAL_PROMPT": "0"}
