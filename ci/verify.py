"""Проверка текущей продуктовой ветки; одинаковый вход для трёх CI."""
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.clean_artifacts import cleanup


def main():
    cleanup(ROOT / "artifacts")
    variant = json.loads((ROOT / "variant.json").read_text())
    project = "verify-" + uuid.uuid4().hex[:10]
    output = ROOT / "artifacts" / project
    output.mkdir(parents=True)
    env = dict(os.environ, LAB_PROJECT=project, LAB_PORT="0", LAB_DB_PORT="0", LAB_DEFECTS="all", PYTHONUTF8="1")
    compose = ["docker", "compose", "-p", project]
    service, port = ("app", "8000") if variant["architecture"] == "monolith" else ("web", "80")
    failed = False
    try:
        subprocess.run(compose + ["up", "-d", "--build", "--wait", "--wait-timeout", "150"], cwd=ROOT, env=env, check=True)
        binding = subprocess.check_output(compose + ["port", service, port], cwd=ROOT, env=env, text=True).strip()
        env["BASE_URL"] = "http://" + binding
        env["ARTIFACT_DIR"] = str(output / "console")
        groups = ["quality/unit", "quality/api/test_contract.py", "quality/ui"]
        if variant["state"] == "buggy":
            groups += ["--ignore=quality/unit/test_policy.py", "-k", "not test_d07 and not test_d08"]
        else:
            groups += ["quality/api/test_defects.py"]
        if variant["architecture"] != "microservices":
            db_binding = subprocess.check_output(compose + ["port", "db", "5432"], cwd=ROOT, env=env, text=True).strip()
            env["SQL_DATABASE_URL"] = "postgresql://lab:" + env.get("LAB_DB_PASSWORD", "lab-local-only") + "@" + db_binding + "/lab"
            groups += ["quality/sql"]
        code = subprocess.call([sys.executable, "scripts/check.py", *groups, "--junitxml=" + str(output / "tests.xml"),
            "--alluredir=" + str(output / "allure"), "--screenshot=only-on-failure", "--tracing=retain-on-failure", "--output=" + str(output / "browser")], cwd=ROOT, env=env)
        failed |= code != 0
        if variant["state"] == "buggy":
            env["OBSERVER_REPORT"] = str(output / "defects.json")
            code = subprocess.call([sys.executable, "scripts/check.py", "quality/api/test_defects.py", "quality/ui/test_interface.py", "-k", "test_d0",
                "-p", "grader.observer", "--junitxml=" + str(output / "expected-defects.xml")], cwd=ROOT, env=env)
            observed = json.loads((output / "defects.json").read_text(encoding="utf-8"))
            confirmed = code == 1 and len(observed["cases"]) == 8 and all(case["outcome"] == "failed" and case["assertion"] for case in observed["cases"].values())
            failed |= not confirmed
            print("Восемь ожидаемых дефектов подтверждены:", confirmed)
        (output / "result.json").write_text(json.dumps({"status": "failed" if failed else "passed", "variant": variant}, ensure_ascii=False), encoding="utf-8")
        return int(failed)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as error:
        (output / "result.json").write_text(json.dumps({"status": "infrastructure_error", "reason": str(error)}, ensure_ascii=False), encoding="utf-8")
        print("Среда не позволила проверить стенд:", str(error), file=sys.stderr)
        return 2
    finally:
        result = subprocess.run(compose + ["logs", "--no-color"], cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
        (output / "compose.log").write_text(result.stdout + result.stderr, encoding="utf-8")
        for app in (["identity", "tickets"] if variant["architecture"] == "microservices" else ["app"]):
            subprocess.run(compose + ["cp", f"{app}:/app/logs", str(output / f"logs-{app}")], cwd=ROOT, env=env, capture_output=True)
        subprocess.run(compose + ["down", "--volumes", "--remove-orphans"], cwd=ROOT, env=env)


if __name__ == "__main__":
    raise SystemExit(main())
