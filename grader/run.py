"""Доверенный запускатель: временные стенды и отдельный контейнер студента."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from grader.result import REQUIREMENTS, assess
from scripts.clean_artifacts import cleanup
from scripts.runtime_directory import runtime_directory


def command(args, cwd=ROOT, env=None, timeout=900):
    """Выполнить команду с ограничением времени; неуспех инфраструктуры должен давать диагностируемую ошибку."""
    result = subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    if result.returncode:
        raise RuntimeError(f"Команда {args[0:3]} завершилась с кодом {result.returncode}: {result.stderr[-3000:]}")
    return result.stdout


def snapshot(ref, destination, repository=ROOT):
    """Распаковать только Git-коммит с безопасным tar-фильтром; .git и незакоммиченные секреты не передаются."""
    import io
    import tarfile
    archive = subprocess.check_output(["git", "archive", ref], cwd=repository)
    with tarfile.open(fileobj=io.BytesIO(archive)) as contents:
        contents.extractall(destination, filter="data")


def require_runtime():
    """Проверяем большую зависимость до создания временных стендов."""
    command(["docker", "info", "--format", "{{.ServerVersion}}"], timeout=30)
    try:
        command(["docker", "image", "inspect", "mini-tickets-grader:1.0"], timeout=30)
    except RuntimeError as error:
        raise RuntimeError("Нет образа оценщика. Выполните .\\scripts\\Prepare-Lab.ps1 -Grader; затем повторите проверку.") from error


def run_submission(source, directory, network, target, name, reverse=False, selection=None):
    """Запустить работу без Docker socket и доступа к БД, сохранить результат и отличить отказ Docker от тестового падения."""
    directory.mkdir(parents=True, exist_ok=True)
    # На Linux каталог bind-mount должен быть доступен непривилегированному пользователю.
    directory.chmod(0o777)
    env = ["-e", f"BASE_URL=http://{target}", "-e", "OBSERVER_REPORT=/results/observed.json", "-e", "ARTIFACT_DIR=/results/console"]
    if reverse:
        env += ["-e", "REVERSE_TEST_ORDER=1"]
    args = ["docker", "run", "--name", name, "--rm", "--network", network, "--read-only", "--cap-drop=ALL", "--security-opt=no-new-privileges",
        "--pids-limit=256", "--memory=2g", "--cpus=2", "--shm-size=512m", "--tmpfs", "/tmp:rw,nosuid,size=512m",
        "-v", f"{source.resolve()}:/submission:ro", "-v", f"{directory.resolve()}:/results", *env, "mini-tickets-grader:1.0", *(selection or ["tests"])]
    try:
        result = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    except subprocess.TimeoutExpired:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True)
        return {"infrastructure_error": True, "reason": "Истёк лимит выполнения"}
    (directory / "runner.log").write_text(result.stdout + result.stderr, encoding="utf-8")
    if result.returncode in {125, 126, 127}:
        return {"infrastructure_error": True, "exit_code": result.returncode,
                "reason": "Контейнер тестов не запустился; см. runner.log", "cases": {}}
    report = directory / "observed.json"
    if not report.exists():
        return {"exit_code": result.returncode or 3, "cases": {}}
    payload = json.loads(report.read_text(encoding="utf-8"))
    payload["exit_code"] = result.returncode
    return payload


def scenario(architecture, state, defects, submission, output, reverse=False, refs=None):
    """Поднять один закреплённый вариант с чистой БД, выполнить работу/контроль и экспортировать логи до очистки."""
    label = f"{architecture}-{state}-{defects}{'-repeat' if reverse else ''}"
    run_id = "grade-" + uuid.uuid4().hex[:12]
    report_dir = output / label / run_id
    report_dir.mkdir(parents=True, exist_ok=True)
    with runtime_directory("mini-tickets") as work:
        ref = (refs or {}).get(f"{architecture}/{state}", f"{architecture}/{state}")
        env = dict(os.environ, LAB_PROJECT=run_id, LAB_DEFECTS=defects, LAB_PORT="0", LAB_DB_PORT="0")
        compose = ["docker", "compose", "-p", run_id]
        frontend = "app" if architecture == "monolith" else "web"
        target = "app:8000" if architecture == "monolith" else "web:80"
        network_created = False
        try:
            snapshot(ref, work)
            command(compose + ["up", "-d", "--build", "--wait", "--wait-timeout", "150"], cwd=work, env=env)
            # Браузер и тесты видят только HTTP-вход. БД остаётся в сети приложения.
            command(["docker", "network", "create", "--internal", run_id + "-tests"])
            network_created = True
            container = command(compose + ["ps", "-q", frontend], cwd=work, env=env).strip()
            command(["docker", "network", "connect", "--alias", frontend, run_id + "-tests", container])
            result = run_submission(submission, report_dir / "student", run_id + "-tests", target, run_id + "-student", reverse)
            if state == "buggy":
                control = run_submission(work, report_dir / "control", run_id + "-tests", target, run_id + "-control",
                    selection=["quality/api/test_defects.py", "quality/ui/test_interface.py", "-k", defects.lower()])
                result["control_confirmed"] = control.get("exit_code") == 1 and any(
                    case["outcome"] == "failed" and case.get("assertion") for case in control.get("cases", {}).values())
            result["source_commit"] = command(["git", "rev-parse", ref]).strip()
            return result
        except (RuntimeError, subprocess.TimeoutExpired, ValueError) as error:
            (report_dir / "infrastructure.log").write_text(str(error), encoding="utf-8")
            return {"infrastructure_error": True, "reason": str(error)}
        finally:
            if (work / "compose.yaml").exists():
                logs = subprocess.run(compose + ["logs", "--no-color"], cwd=work, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
                (report_dir / "compose.log").write_text(logs.stdout + logs.stderr, encoding="utf-8")
                for service in (["identity", "tickets"] if architecture == "microservices" else ["app"]):
                    subprocess.run(compose + ["cp", f"{service}:/app/logs", str(report_dir / f"logs-{service}")], cwd=work, env=env, capture_output=True)
                subprocess.run(compose + ["down", "--volumes", "--remove-orphans"], cwd=work, env=env, capture_output=True)
            if network_created:
                subprocess.run(["docker", "network", "rm", run_id + "-tests"], capture_output=True)


def main():
    """Оценить сохранённый коммит: эталоны, обратный порядок, назначенные дефекты и итоговые коды 0/1/2."""
    cleanup(ROOT / "artifacts")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--submission", type=Path, required=True)
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--defects", default=",".join(REQUIREMENTS))
    parser.add_argument("--threshold", type=float, default=0.75)
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/grading")
    parser.add_argument("--refs", type=Path, default=ROOT / "releases/1.0.0.json", help="JSON с закреплёнными коммитами шести вариантов")
    args = parser.parse_args()
    defects = args.defects.split(",")
    if not args.submission.is_dir() or not defects or not set(defects) <= REQUIREMENTS.keys() or not 0 <= args.threshold <= 1:
        parser.error("Проверьте каталог работы, дефекты и порог")
    args.output.mkdir(parents=True, exist_ok=True)
    try:
        require_runtime()
    except (RuntimeError, OSError, subprocess.TimeoutExpired) as error:
        data = {"status": "infrastructure_error", "reason": str(error)}
        (args.output / "grade.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        (args.output / "grade.md").write_text("# Проверка не началась\n\n" + str(error) + "\n", encoding="utf-8")
        print(str(error), file=sys.stderr)
        return 2
    refs = json.loads(args.refs.read_text(encoding="utf-8"))
    source_commit = command(["git", "rev-parse", "HEAD"], cwd=args.submission).strip()
    with runtime_directory("mini-submission") as source_path:
        snapshot(source_commit, source_path, repository=args.submission)
        baselines, mutants = {}, {}
        architectures = ["monolith", "client-server", "microservices"]
        for architecture in architectures:
            print(f"Исправленный вариант: {architecture}", flush=True)
            baselines[architecture] = scenario(architecture, "fixed", "none", source_path, args.output, refs=refs)
            # При отказе Docker остальные дефекты не дадут полезного измерения.
            if baselines[architecture].get("infrastructure_error") or baselines[architecture].get("exit_code") != 0:
                break
        baseline_ok = len(baselines) == 3 and all(run.get("exit_code") == 0 for run in baselines.values())
        if baseline_ok:
            baselines["repeat"] = scenario("monolith", "fixed", "none", source_path, args.output, reverse=True, refs=refs)
            baseline_ok = baselines["repeat"].get("exit_code") == 0
        if baseline_ok:
            for defect in defects:
                mutants[defect] = []
                for architecture in architectures if args.full else ["monolith"]:
                    print(f"Проверка {defect}: {architecture}", flush=True)
                    mutants[defect].append(scenario(architecture, "buggy", defect, source_path, args.output, refs=refs))
    verdict = assess(baselines, mutants, defects, args.threshold)
    data = {**verdict.to_dict(), "baselines": baselines, "mutants": mutants, "refs": refs,
        "grader_commit": command(["git", "rev-parse", "HEAD"]).strip(),
        "submission_commit": source_commit}
    (args.output / "grade.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.output / "grade.md").write_text(f"# Результат проверки\n\nСтатус: {verdict.status}. Обнаружение: {verdict.score}%.\n\n{verdict.reason}\n\nОбнаружено: {', '.join(verdict.detected) or 'нет'}. Пропущено: {', '.join(verdict.missed) or 'нет'}.\n", encoding="utf-8")
    print(json.dumps(verdict.to_dict(), ensure_ascii=False))
    return 0 if verdict.status == "passed" else 2 if verdict.status == "infrastructure_error" else 1


if __name__ == "__main__":
    raise SystemExit(main())
