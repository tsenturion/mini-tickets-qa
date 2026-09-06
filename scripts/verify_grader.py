"""Репетиция контейнерного оценщика: правильная, постоянно падающая и пустая работы.

Сначала самостоятельно подготовьте большой образ через Prepare-Lab.ps1 -Grader.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from grader.run import command, require_runtime


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full", action="store_true", help="Проверить хорошую работу на всех восьми дефектах трёх архитектур")
    args = parser.parse_args()
    try:
        require_runtime()
    except (RuntimeError, OSError, subprocess.TimeoutExpired) as error:
        print(str(error), file=sys.stderr)
        return 2
    for kind in ["reference", "always-fails", "empty"]:
        print(f"Демонстрационная работа: {kind}", flush=True)
        with tempfile.TemporaryDirectory(prefix="mini-grader-example-") as temporary:
            source = Path(temporary)
            tests = source / "tests"
            tests.mkdir()
            if kind == "reference":
                shutil.copyfile(ROOT / "quality/conftest.py", source / "conftest.py")
                (source / "quality").mkdir()
                shutil.copyfile(ROOT / "quality/support.py", source / "quality/support.py")
                shutil.copyfile(ROOT / "quality/api/test_defects.py", tests / "test_api.py")
                shutil.copyfile(ROOT / "quality/ui/test_interface.py", tests / "test_ui.py")
            else:
                (tests / "test_sample.py").write_text("import pytest\n@pytest.mark.api\ndef test_failure():\n    assert False\n" if kind == "always-fails" else "# Намеренно пустая учебная работа.\n", encoding="utf-8")
            command(["git", "init", "-b", "main"], cwd=source)
            command(["git", "add", "."], cwd=source)
            command(["git", "-c", "user.name=Учебная проверка", "-c", "user.email=qa@example.test", "commit", "-m", "Создана демонстрационная работа"], cwd=source)
            output = ROOT / "artifacts/grader-self-test" / kind
            options = ["--full"] if args.full and kind == "reference" else ["--defects", "D01,D07"] if kind == "reference" else ["--defects", "D01"]
            result = subprocess.run([sys.executable, "grader/run.py", "--submission", str(source), "--output", str(output), *options], cwd=ROOT)
            grade = json.loads((output / "grade.json").read_text(encoding="utf-8"))
            expected = "passed" if kind == "reference" else "invalid_submission"
            assert grade["status"] == expected, grade.get("reason")
            assert result.returncode == (0 if kind == "reference" else 1)
            if kind == "reference":
                assert grade["score"] == 100
    print("Оценщик принимает правильные тесты и отклоняет постоянное падение и пустую работу.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
