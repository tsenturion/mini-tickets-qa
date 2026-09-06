"""Сборка вариантов из общего проверенного выпуска без слияния архитектур."""
import argparse
import copy
import json
from pathlib import Path
import shutil
import subprocess

import yaml

ROOT = Path(__file__).resolve().parents[1]
ARCHITECTURES = ["monolith", "client-server", "microservices"]


def configure(directory, architecture, state):
    template = yaml.safe_load((ROOT / "variants/compose-base.yaml").read_text(encoding="utf-8"))
    services = template["services"]
    app = services["app"]
    app["build"] = {"context": ".", "args": {"VITE_DEFECTS": "${LAB_DEFECTS:-all}" if state == "buggy" else "none"}}
    if state == "buggy":
        app["environment"]["LAB_DEFECTS"] = "${LAB_DEFECTS:-all}"
        shutil.copyfile(ROOT / "variants/buggy-policy.txt", directory / "backend/policy.py")
        shutil.copyfile(ROOT / "variants/buggy-behavior.txt", directory / "frontend/src/behavior.js")
    if architecture != "monolith":
        del app["ports"]
        web = {"build": {"context": ".", "dockerfile": "deploy/Dockerfile.web", "args": app["build"]["args"]},
            "ports": ["127.0.0.1:${LAB_PORT:-8000}:80"], "depends_on": {"app": {"condition": "service_healthy"}},
            "healthcheck": {"test": ["CMD", "wget", "-q", "-O", "/dev/null", "http://127.0.0.1/health/ready"], "interval": "3s", "timeout": "5s", "retries": 40},
            "logging": {"driver": "local", "options": {"max-size": "5m", "max-file": "3"}}}
        services["web"] = web
        shutil.copyfile(ROOT / f"deploy/nginx-{'micro' if architecture == 'microservices' else 'client'}.conf", directory / "deploy/nginx.conf")
    if architecture == "microservices":
        identity = copy.deepcopy(app)
        tickets = copy.deepcopy(app)
        identity["environment"].update(SERVICE="identity", DATABASE_URL="postgresql+psycopg://identity:identity-local-only@db:5432/identity")
        tickets["environment"].update(SERVICE="tickets", DATABASE_URL="postgresql+psycopg://tickets:tickets-local-only@db:5432/tickets", IDENTITY_URL="http://identity:8000")
        tickets["depends_on"]["identity"] = {"condition": "service_healthy"}
        # Разные каталоги логов исключают конкуренцию двух процессов за ротацию.
        identity["environment"]["LOG_DIR"] = "/app/logs/identity"
        tickets["environment"]["LOG_DIR"] = "/app/logs/tickets"
        services.pop("app")
        services.update(identity=identity, tickets=tickets)
        services["db"]["volumes"].append("./deploy/init-micro.sh:/docker-entrypoint-initdb.d/01-micro.sh:ro")
        web["depends_on"] = {"identity": {"condition": "service_healthy"}, "tickets": {"condition": "service_healthy"}}
    (directory / "compose.yaml").write_text(yaml.safe_dump(template, allow_unicode=True, sort_keys=False), encoding="utf-8")
    (directory / "variant.json").write_text(json.dumps({"architecture": architecture, "state": state, "contract": "1.0.0"}, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="monolith/fixed")
    args = parser.parse_args()
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT).strip():
        raise SystemExit("Сначала сохраните изменения базовой ветки коммитом")
    for architecture in ARCHITECTURES:
        for state in ["fixed", "buggy"]:
            branch = f"{architecture}/{state}"
            if branch == args.base:
                continue
            directory = ROOT / ".worktrees" / branch.replace("/", "-")
            base = args.base if state == "fixed" else f"{architecture}/fixed"
            subprocess.run(["git", "worktree", "add", "-b", branch, str(directory), base], cwd=ROOT, check=True)
            configure(directory, architecture, state)
            subprocess.run(["git", "add", "compose.yaml", "variant.json", "backend/policy.py", "frontend/src/behavior.js", "deploy"], cwd=directory, check=True)
            subprocess.run(["git", "commit", "-m", f"Подготовлен вариант {architecture}: {'исправленный' if state == 'fixed' else 'с учебными дефектами'}"], cwd=directory, check=True)


if __name__ == "__main__":
    main()

