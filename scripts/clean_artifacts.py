"""Удаляет только устаревшие файлы диагностических каталогов указанного проекта."""
import argparse
from pathlib import Path
import time


def cleanup(directory, now=None):
    directory = Path(directory).resolve()
    if directory.name not in {"artifacts", "logs", "test-results"}:
        raise ValueError("Разрешены только каталоги artifacts, logs, test-results")
    cutoff = (time.time() if now is None else now) - 30 * 86400
    count = 0
    if not directory.exists():
        return count
    for path in directory.rglob("*"):
        if path.is_symlink() or directory not in path.resolve().parents:
            continue
        if path.is_file() and path.stat().st_mtime < cutoff:
            path.unlink()
            count += 1
    return count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", nargs="?", default=str(Path(__file__).resolve().parents[1] / "artifacts"))
    args = parser.parse_args()
    print(f"Удалено устаревших диагностических файлов: {cleanup(args.directory)}")

