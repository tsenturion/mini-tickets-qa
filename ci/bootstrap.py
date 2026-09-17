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
    # Каталог сохраняется между сборками одного агента, но изолирован от его
    # системного Python. Повторное создание обновляет служебные файлы venv, не
    # превращая глобальное окружение агента в неявную зависимость pipeline.
    environment = ROOT / ".runtime/ci-venv"
    venv.EnvBuilder(with_pip=True, system_site_packages=False).create(environment)
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")

    # requirements-test.txt задаёт прямые зависимости, а constraints-файл
    # фиксирует всё разрешённое дерево версий. Chromium устанавливается
    # отдельной командой: Python-пакет Playwright содержит драйвер, но не сам
    # совместимый исполняемый браузер.
    commands = [
        [str(python), "-m", "pip", "install", "-r", "requirements-test.txt", "-c", "requirements-test.lock"],
        [str(python), "-m", "playwright", "install", "chromium"],
        [str(python), "ci/verify.py"],
    ]
    for command in commands:
        # Последовательность намеренно fail-fast: запуск verify после неполной
        # установки превратил бы инфраструктурную причину в ложный дефект
        # продукта. Возвращаем исходный код первой неуспешной стадии, чтобы CI
        # сохранил правильную точку отказа.
        result = subprocess.run(command, cwd=ROOT, env=dict(os.environ, PYTHONUTF8="1"))
        if result.returncode:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
