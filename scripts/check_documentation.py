"""Проверить наличие поясняющих docstring во всём авторском Python-коде.

Проверяются также вложенные функции и шаблон дефектной политики.
Генерируемые каталоги, виртуальные среды и копии работ не обходятся.
"""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRS = ("backend", "ci", "grader", "load", "migrations", "quality", "scripts", "student-template")


def missing_docstrings(root=ROOT):
    """Вернуть точные места пропусков; наличие текста не заменяет содержательное ревью преподавателя."""
    errors = []
    paths = [path for directory in SOURCE_DIRS for path in (root / directory).rglob("*.py")]
    paths.append(root / "variants/buggy-policy.txt")
    for path in sorted(paths):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                if not ast.get_docstring(node):
                    errors.append(f"{path.relative_to(root)}:{getattr(node, 'lineno', 1)} {getattr(node, 'name', 'модуль')}")
    return errors


def main():
    """Завершить проверку ненулевым кодом, если новый код не получил документацию."""
    errors = missing_docstrings()
    print("\n".join(errors) if errors else "Docstring есть у всех модулей, классов и функций Python.")
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
