"""Изолировать зависимости на постоянном агенте GitLab/Jenkins и проверить продукт.

Глобальный Python используется только для создания venv: чужие проекты агента
не получают новые версии pytest, FastAPI или зависимостей браузера.
"""
import os
from pathlib import Path
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parents[1]


def main():
    """Подготовить собственную среду агента и вернуть настоящий код проверки стенда."""
    environment = ROOT / ".runtime/ci-venv"
    venv.EnvBuilder(with_pip=True, system_site_packages=False).create(environment)
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    commands = [
        [str(python), "-m", "pip", "install", "-r", "requirements-test.txt", "-c", "requirements-test.lock"],
        [str(python), "-m", "playwright", "install", "chromium"],
        [str(python), "ci/verify.py"],
    ]
    for command in commands:
        # Не запускать тесты после ошибки установки: иначе причина будет ошибочно отнесена к продукту.
        result = subprocess.run(command, cwd=ROOT, env=dict(os.environ, PYTHONUTF8="1"))
        if result.returncode:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
