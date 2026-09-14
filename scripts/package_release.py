"""Собирает воспроизводимый набор файлов для публикации учебного выпуска."""

import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys

try:
    from validate_release import BRANCHES, ReleaseValidationError, validate_release
except ModuleNotFoundError:
    from scripts.validate_release import BRANCHES, ReleaseValidationError, validate_release


ROOT = Path(__file__).resolve().parents[1]


class ReleasePackagingError(ValueError):
    """Сообщает, что пакет выпуска нельзя безопасно сформировать."""


def archive_name(version: str, branch: str) -> str:
    """Вернуть имя архива, однозначно связывающее вариант с выпуском."""
    architecture, state = branch.split("/", maxsplit=1)
    return f"mini-tickets-qa-{version}-{architecture}-{state}.zip"


def prepare_output(root: Path, output: Path) -> Path:
    """Создать пустой каталог результата, не затрагивая существующие файлы."""
    resolved_root = root.resolve()
    resolved_output = output.resolve()
    releases_directory = resolved_root / "releases"
    if resolved_output == resolved_root or resolved_output.is_relative_to(releases_directory):
        raise ReleasePackagingError("Каталог результата не должен совпадать с корнем проекта или находиться в releases.")
    if resolved_output.exists() and not resolved_output.is_dir():
        raise ReleasePackagingError(f"Путь результата должен быть каталогом: {resolved_output}.")
    if resolved_output.exists() and any(resolved_output.iterdir()):
        raise ReleasePackagingError(f"Каталог результата должен быть пустым: {resolved_output}.")
    resolved_output.mkdir(parents=True, exist_ok=True)
    return resolved_output


def run_git_archive(root: Path, commit: str, destination: Path, prefix: str) -> None:
    """Сохранить состояние точного Git-коммита в ZIP без обращения к сети."""
    result = subprocess.run(
        ["git", "archive", "--format=zip", f"--prefix={prefix}", "--output", str(destination), commit],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "Git archive завершился с ошибкой."
        raise ReleasePackagingError(message)


def write_checksums(directory: Path, filenames: list[str]) -> Path:
    """Записать SHA-256 каждого публикуемого файла в стандартном текстовом формате."""
    checksum_path = directory / "SHA256SUMS.txt"
    lines = []
    for filename in filenames:
        digest = hashlib.sha256((directory / filename).read_bytes()).hexdigest()
        lines.append(f"{digest}  {filename}")
    checksum_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return checksum_path


def package_release(root: Path, version: str, output: Path) -> list[Path]:
    """Проверить манифест и собрать JSON, шесть ZIP-архивов и контрольные суммы."""
    manifest = validate_release(root, version)
    directory = prepare_output(root, output)
    manifest_name = f"{version}.json"
    shutil.copyfile(root / "releases" / manifest_name, directory / manifest_name)
    filenames = [manifest_name]
    for branch in BRANCHES:
        filename = archive_name(version, branch)
        run_git_archive(root, manifest[branch], directory / filename, f"mini-tickets-qa-{version}-{branch.replace('/', '-')}/")
        filenames.append(filename)
    checksum_path = write_checksums(directory, filenames)
    return [directory / filename for filename in filenames] + [checksum_path]


def main() -> int:
    """Запустить сборку пакета из командной строки и вернуть код завершения."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True, help="Версия выпуска, например 1.0.0.")
    parser.add_argument("--output", required=True, type=Path, help="Новый или пустой каталог результата.")
    arguments = parser.parse_args()
    try:
        files = package_release(ROOT, arguments.version, arguments.output)
    except (ReleaseValidationError, ReleasePackagingError) as error:
        print(f"Ошибка сборки выпуска: {error}", file=sys.stderr)
        return 1
    print("Собран пакет выпуска:")
    for file in files:
        print(file)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
