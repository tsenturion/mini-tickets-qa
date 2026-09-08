"""Репетиция оценивания на доверенных контрольных тестах и локальном браузере.

Не принимает работы студентов: их код запускается только через контейнерный grader.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from grader.run import command, snapshot
from grader.result import REQUIREMENTS, assess
from scripts.runtime_directory import runtime_directory


def verify(architecture, state, defect, output, reverse=False):
    """Проверить один вариант доверенными тестами на локальном браузере и сохранить доказательства до удаления БД."""
    label = f"{state}-{defect}" + ("-repeat" if reverse else "")
    destination = output / label
    destination.mkdir(parents=True, exist_ok=True)
    project = "matrix-" + uuid.uuid4().hex[:10]
    env = dict(os.environ, LAB_PROJECT=project, LAB_PORT="0", LAB_DB_PORT="0", LAB_DEFECTS=defect, PYTHONUTF8="1")
    env["OBSERVER_REPORT"] = str(destination / "observed.json")
    env["ARTIFACT_DIR"] = str(destination / "console")
    if reverse:
        env["REVERSE_TEST_ORDER"] = "1"
    compose = ["docker", "compose", "-p", project]
    with runtime_directory("matrix") as directory:
        snapshot(f"{architecture}/{state}", directory)
        try:
            build_log = command(compose + ["up", "-d", "--build", "--wait", "--wait-timeout", "150"], cwd=directory, env=env)
            (destination / "build.log").write_text(build_log, encoding="utf-8")
            service, port = ("app", "8000") if architecture == "monolith" else ("web", "80")
            binding = command(compose + ["port", service, port], cwd=directory, env=env).strip()
            env["BASE_URL"] = "http://" + binding
            result = subprocess.run([sys.executable, "scripts/check.py", "quality/api/test_defects.py", "quality/ui/test_interface.py", "-p", "grader.observer", "-q",
                "--junitxml=" + str(destination / "tests.xml"), "--screenshot=only-on-failure", "--output=" + str(destination / "browser")], cwd=directory, env=env,
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
            (destination / "tests.log").write_text(result.stdout + result.stderr, encoding="utf-8")
            observed = json.loads((destination / "observed.json").read_text(encoding="utf-8"))
            observed["exit_code"] = result.returncode
            observed["control_confirmed"] = True
            return observed
        finally:
            for service in (["identity", "tickets"] if architecture == "microservices" else ["app"]):
                subprocess.run(compose + ["cp", f"{service}:/app/logs", str(destination / f"logs-{service}")], cwd=directory, env=env, capture_output=True)
            subprocess.run(compose + ["down", "--volumes", "--remove-orphans"], cwd=directory, env=env, capture_output=True)


def main():
    """Проверить эталон дважды и восемь одиночных дефектов одной архитектуры без подмены студенческого контейнерного запуска."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--architecture", choices=["monolith", "client-server", "microservices"], required=True)
    args = parser.parse_args()
    output = ROOT / "artifacts/matrix" / args.architecture
    print(f"{args.architecture}: исправленный вариант", flush=True)
    baseline = verify(args.architecture, "fixed", "none", output)
    repeat = verify(args.architecture, "fixed", "none", output, reverse=True)
    mutants = {}
    for defect in REQUIREMENTS:
        print(f"{args.architecture}: {defect}", flush=True)
        mutants[defect] = [verify(args.architecture, "buggy", defect, output)]
    verdict = assess({"fixed": baseline, "repeat": repeat}, mutants, list(REQUIREMENTS), threshold=1)
    (output / "verdict.json").write_text(json.dumps(verdict.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(verdict.to_dict(), ensure_ascii=False), flush=True)
    return int(verdict.status != "passed")


if __name__ == "__main__":
    raise SystemExit(main())
