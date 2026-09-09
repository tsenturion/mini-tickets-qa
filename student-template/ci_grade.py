"""Адаптер демонстрационного MR; итоговый доверенный запуск настраивает преподаватель."""
import base64
import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import urlsplit

def clone_environment(url, environment):
    """Передать короткоживущий job token только своему GitLab и только процессу клонирования."""
    result = dict(environment, GIT_TERMINAL_PROMPT="0")
    token = result.get("CI_JOB_TOKEN")
    if token:
        target, server = urlsplit(url), urlsplit(result.get("CI_SERVER_URL", ""))
        if target.username or target.password or (target.scheme, target.hostname, target.port) != (server.scheme, server.hostname, server.port):
            raise ValueError("QA_PRODUCT_URL должен указывать на тот же GitLab, что CI_SERVER_URL, без пароля в адресе")
        if target.scheme != "https" and not (target.scheme == "http" and target.hostname in {"localhost", "127.0.0.1", "::1"}):
            raise ValueError("Для передачи job token нужен HTTPS; HTTP допустим только на loopback")
        # Секрет не попадает в URL, аргументы команды или сохранённый .git/config.
        index = int(result.get("GIT_CONFIG_COUNT", "0"))
        credential = base64.b64encode(("gitlab-ci-token:" + token).encode()).decode()
        result.update({"GIT_CONFIG_COUNT": str(index + 2),
                       f"GIT_CONFIG_KEY_{index}": f"http.{server.scheme}://{server.netloc}/.extraHeader",
                       f"GIT_CONFIG_VALUE_{index}": "Authorization: Basic " + credential,
                       f"GIT_CONFIG_KEY_{index + 1}": "http.followRedirects",
                       f"GIT_CONFIG_VALUE_{index + 1}": "false"})
    return result


def main():
    """Получить доверенный продукт и вернуть код контейнерного оценщика без подмены статуса."""
    product = Path("product")
    url = os.environ["QA_PRODUCT_URL"]
    subprocess.run(["git", "clone", url, str(product)], check=True, env=clone_environment(url, os.environ))
    subprocess.run(["git", "checkout", "--detach", os.environ["QA_PRODUCT_REF"]], cwd=product, check=True)
    subprocess.run(["docker", "build", "-f", "grader/Dockerfile", "-t", "mini-tickets-grader:1.0", "."], cwd=product, check=True)
    subprocess.run([sys.executable, "scripts/freeze_release.py"], cwd=product, check=True)
    return subprocess.call([sys.executable, "grader/run.py", "--submission", "..", "--refs", "artifacts/release-lock.json"], cwd=product)


if __name__ == "__main__":
    raise SystemExit(main())
