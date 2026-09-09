"""Проверить каталоги контейнера до загрузки кода работы и затем запустить Pytest."""
import json
from pathlib import Path
import stat
import subprocess
import sys
import tempfile

MOUNT_ERROR = 78
PYTEST_OPTIONS = [
    "-c", "/runner/pytest.ini", "--rootdir=/submission", "--confcutdir=/submission",
    "-p", "pytest_base_url.plugin", "-p", "pytest_playwright.pytest_playwright",
    "-p", "pytest_timeout", "-p", "allure_pytest.plugin", "-p", "observer", "--timeout=40",
    "--screenshot=only-on-failure", "--tracing=retain-on-failure", "--output=/results/browser",
    "--junitxml=/results/junit.xml", "--alluredir=/results/allure",
]


def check_mounts(source=Path("/submission"), results=Path("/results")):
    """Проверить фактическое чтение работы и запись отчёта, не исполняя присланный код."""
    if not stat.S_ISDIR(source.stat().st_mode):
        raise NotADirectoryError("Каталог работы не подключён")
    # is_dir() скрывает часть ошибок ОС; stat/iterdir сохраняют причину EIO/ACL.
    next(source.iterdir(), None)
    with tempfile.TemporaryFile(dir=results) as probe:
        probe.write(b"ready")
        probe.flush()


def main(arguments=None):
    """Отделить отказ bind mount от пустой работы, ошибки импорта и настоящего AssertionError."""
    try:
        check_mounts()
    except OSError as error:
        print(json.dumps({"event": "grader_mount_error", "error_type": type(error).__name__,
                          "errno": error.errno, "message": "Контейнер не может прочитать работу или записать отчёт"},
                         ensure_ascii=False), file=sys.stderr)
        return MOUNT_ERROR
    return subprocess.call([sys.executable, "-m", "pytest", *PYTEST_OPTIONS,
                            *(sys.argv[1:] if arguments is None else arguments)], cwd="/submission")


if __name__ == "__main__":
    raise SystemExit(main())
