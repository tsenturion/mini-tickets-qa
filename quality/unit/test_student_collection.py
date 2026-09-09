"""Регрессия конфликта одноимённых API/UI-файлов в стартовой работе студента."""
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("config", ["grader/pytest.ini", "student-template/pytest.ini"])
def test_starter_collects_in_both_configs(config):
    """Два примера собираются и локально, и с доверенной конфигурацией оценщика без запуска приложения."""
    product = ROOT
    student = product / "student-template"
    result = subprocess.run([sys.executable, "-m", "pytest", "-c", str(product / config),
        "--rootdir=" + str(student), "--confcutdir=" + str(student), "-p", "no:cacheprovider",
        "--collect-only", "-q", "tests"], cwd=student,
        env=dict(os.environ, PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTHONUTF8="1"),
        capture_output=True, text=True, encoding="utf-8", timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "2 tests collected" in result.stdout
