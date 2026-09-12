"""Проверка создания самостоятельной работы без изменения продукта и пользовательских настроек Git."""
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from scripts.runtime_directory import runtime_directory

ROOT = Path(__file__).resolve().parents[2]
POWERSHELL = shutil.which("pwsh")
pytestmark = pytest.mark.skipif(not POWERSHELL, reason="Для проверки генератора нужен PowerShell 7")


@pytest.fixture
def workspace(tmp_path):
    """Скопировать только учебную заготовку в собственную временную среду и изолировать Git."""
    with runtime_directory("student-repo", tmp_path) as directory:
        product = directory / "product"
        script = product / "scripts/New-StudentRepo.ps1"
        script.parent.mkdir(parents=True)
        shutil.copyfile(ROOT / "scripts/New-StudentRepo.ps1", script)
        files = subprocess.check_output(["git", "ls-files", "--", "student-template"],
            cwd=ROOT, text=True, encoding="utf-8").splitlines()
        for name in files:
            destination = product / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, destination)
        environment = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1",
            GIT_CONFIG_COUNT="1", GIT_CONFIG_KEY_0="commit.gpgsign", GIT_CONFIG_VALUE_0="false",
            GIT_AUTHOR_NAME="Проверка", GIT_COMMITTER_NAME="Проверка",
            GIT_AUTHOR_EMAIL="qa@example.test", GIT_COMMITTER_EMAIL="qa@example.test",
            PYTHONUTF8="1")
        yield product, directory, environment


def generate(workspace, destination):
    """Запустить настоящий PowerShell из другого каталога, сохранив диагностику при ошибке."""
    product, caller, environment = workspace
    return subprocess.run([POWERSHELL, "-NoProfile", "-NonInteractive", "-File",
        str(product / "scripts/New-StudentRepo.ps1"), "-Destination", destination],
        cwd=caller, env=environment, capture_output=True, text=True, encoding="utf-8", timeout=25)


@pytest.mark.parametrize("absolute", [True, False], ids=["absolute", "relative"])
def test_repo_contains_root_ci_and_only_main(workspace, absolute):
    """Оба вида пути с пробелами дают самостоятельную main с полным шаблоном и собираемыми тестами."""
    product, caller, environment = workspace
    target = (caller if absolute else product) / "my testing work"
    result = generate(workspace, str(target) if absolute else target.name)
    assert result.returncode == 0, result.stdout + result.stderr
    files = subprocess.check_output(["git", "ls-files"], cwd=target, text=True).splitlines()
    assert {".github/workflows/qa.yml", ".gitlab-ci.yml", "ci_grade.py", "README.md"} <= set(files)
    expected = {path.relative_to(product / "student-template").as_posix()
                for path in (product / "student-template").rglob("*") if path.is_file()}
    assert set(files) == expected
    for name in files:
        assert (target / name).read_bytes() == (product / "student-template" / name).read_bytes()
    assert subprocess.check_output(["git", "branch", "--format=%(refname:short)"], cwd=target).strip() == b"main"
    assert subprocess.check_output(["git", "remote"], cwd=target).strip() == b""
    assert subprocess.check_output(["git", "status", "--porcelain"], cwd=target).strip() == b""
    collected = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider"],
        cwd=target, env=dict(environment, PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"),
        capture_output=True, text=True, encoding="utf-8", timeout=15)
    assert collected.returncode == 0, collected.stdout + collected.stderr
    assert "2 tests collected" in collected.stdout


def test_existing_destination_is_not_modified(workspace):
    """Чужой каталог остаётся нетронутым, а отказ явно виден в журнале PowerShell."""
    product, _, _ = workspace
    target = product / "existing"
    target.mkdir()
    marker = target / "оставить.txt"
    marker.write_text("Не перезаписывать", encoding="utf-8")
    result = generate(workspace, target.name)
    assert result.returncode != 0
    assert "Каталог уже существует" in result.stderr
    assert marker.read_text(encoding="utf-8") == "Не перезаписывать"
    assert list(target.iterdir()) == [marker]


@pytest.mark.parametrize("destination", ["", "   "], ids=["empty", "whitespace"])
def test_empty_destination_is_rejected(workspace, destination):
    """Пустой путь не превращается в запись поверх корня продукта."""
    product, _, _ = workspace
    result = generate(workspace, destination)
    assert result.returncode != 0
    assert not (product / ".git").exists()
    assert not (product / "README.md").exists()
