import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    env = dict(os.environ, PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTHONUTF8="1")
    args = sys.argv[1:] or ["quality/unit"]
    command = [sys.executable, "-m", "pytest", "-p", "pytest_base_url.plugin", "-p", "pytest_playwright.pytest_playwright",
        "-p", "pytest_timeout", "-p", "allure_pytest.plugin", "--timeout=40", *args]
    return subprocess.call(command, cwd=ROOT, env=env)


if __name__ == "__main__":
    raise SystemExit(main())
