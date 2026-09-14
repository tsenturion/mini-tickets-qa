"""Проверяет манифест выпуска до его публикации."""

import argparse
import json
from collections.abc import Callable, Mapping
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
BRANCHES = (
    "monolith/fixed",
    "monolith/buggy",
    "client-server/fixed",
    "client-server/buggy",
    "microservices/fixed",
    "microservices/buggy",
)
VERSION_PATTERN = re.compile(r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\Z")
SHA_PATTERN = re.compile(r"[0-9a-f]{40}\Z")


class ReleaseValidationError(ValueError):
    """Сообщает, что выпуск нельзя публиковать в текущем виде."""


def validate_version(version: str) -> None:
    """Проверить, что имя выпуска имеет неизменяемый формат MAJOR.MINOR.PATCH."""
    if not VERSION_PATTERN.fullmatch(version):
        raise ReleaseValidationError(
            "Версия должна иметь формат MAJOR.MINOR.PATCH без префикса: "
            f"получено {version!r}."
        )


def load_manifest(root: Path, version: str) -> dict[str, str]:
    """Прочитать и проверить схему манифеста указанного выпуска."""
    validate_version(version)
    manifest_path = root / "releases" / f"{version}.json"
    if not manifest_path.is_file():
        raise ReleaseValidationError(f"Не найден манифест выпуска: {manifest_path}.")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ReleaseValidationError(f"Манифест {manifest_path} содержит некорректный JSON: {error.msg}.") from error
    if not isinstance(manifest, dict):
        raise ReleaseValidationError("Манифест должен быть JSON-объектом.")
    expected = set(BRANCHES)
    actual = set(manifest)
    if actual != expected:
        missing = ", ".join(sorted(expected - actual)) or "нет"
        unexpected = ", ".join(sorted(actual - expected)) or "нет"
        raise ReleaseValidationError(
            "Манифест должен содержать только шесть веток выпуска; "
            f"отсутствуют: {missing}; лишние: {unexpected}."
        )
    for branch in BRANCHES:
        commit = manifest[branch]
        if not isinstance(commit, str) or not SHA_PATTERN.fullmatch(commit):
            raise ReleaseValidationError(f"Для ветки {branch} требуется SHA-1 из 40 строчных шестнадцатеричных символов.")
    return manifest


def run_git(root: Path, arguments: list[str]) -> str:
    """Выполнить Git без сети и вернуть стандартный вывод при успехе."""
    result = subprocess.run(
        ["git", *arguments],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "Git завершился с ошибкой."
        raise ReleaseValidationError(message)
    return result.stdout


def validate_commit(root: Path, branch: str, commit: str, runner: Callable[[Path, list[str]], str] = run_git) -> None:
    """Убедиться, что коммит существует и описывает вариант, указанный ключом манифеста."""
    try:
        runner(root, ["cat-file", "-e", f"{commit}^{{commit}}"])
    except ReleaseValidationError as error:
        raise ReleaseValidationError(f"Коммит {commit} для {branch} недоступен: {error}.") from error
    try:
        variant = json.loads(runner(root, ["show", f"{commit}:variant.json"]))
    except (ReleaseValidationError, json.JSONDecodeError) as error:
        raise ReleaseValidationError(f"Не удалось прочитать variant.json коммита {commit} для {branch}.") from error
    architecture, state = branch.split("/", maxsplit=1)
    if not isinstance(variant, Mapping) or variant.get("architecture") != architecture or variant.get("state") != state:
        raise ReleaseValidationError(
            f"Коммит {commit} не соответствует ветке {branch}: "
            "в variant.json указана другая архитектура или состояние."
        )


def validate_release(root: Path, version: str, runner: Callable[[Path, list[str]], str] = run_git) -> dict[str, str]:
    """Проверить манифест и все зафиксированные в нём варианты продукта."""
    manifest = load_manifest(root, version)
    for branch in BRANCHES:
        validate_commit(root, branch, manifest[branch], runner)
    return manifest


def main() -> int:
    """Запустить проверку из командной строки и вернуть код завершения."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True, help="Версия выпуска, например 1.0.0.")
    arguments = parser.parse_args()
    try:
        validate_release(ROOT, arguments.version)
    except ReleaseValidationError as error:
        print(f"Ошибка проверки выпуска: {error}", file=sys.stderr)
        return 1
    print(f"Манифест выпуска {arguments.version} проверен.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
