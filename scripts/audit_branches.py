"""Проверка количества вариантов и синхронности общих учебных материалов."""
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
expected = {f"{architecture}/{state}" for architecture in ["monolith", "client-server", "microservices"] for state in ["fixed", "buggy"]}


def git(*args):
    """Прочитать метаданные Git для сравнения шести вариантов, не переключая рабочую ветку."""
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True, encoding="utf-8").strip()


local = set(git("for-each-ref", "--format=%(refname:short)", "refs/heads").splitlines())
remote = {name.removeprefix("refs/remotes/origin/") for name in git("for-each-ref", "--format=%(refname)", "refs/remotes/origin").splitlines() if name != "refs/remotes/origin/HEAD"}
actual = local | remote
if actual != expected:
    raise SystemExit(f"Ожидалось шесть веток: {sorted(expected)}; найдено: {sorted(actual)}")
paths = ["README.md", "scripts/Prepare-Lab.ps1", "scripts/Prepare-LocalCI.ps1", "scripts/verify_grader.py",
         "infra/ci/runner-template.toml", "Jenkinsfile", "ci/grading.Jenkinsfile", "grader/entrypoint.py",
         "contract/openapi.json", "docs/ТРЕБОВАНИЯ.md", "docs/ПРАКТИКУМ.md", "grader/result.py", "grader/observer.py",
         "ci/verify.py", "quality/api/test_defects.py", "quality/ui/test_interface.py", "frontend/src/App.vue", "requirements.lock", "requirements-test.lock"]
for branch in sorted(expected):
    ref = branch if branch in local else f"origin/{branch}"
    base = "monolith/fixed" if "monolith/fixed" in local else "origin/monolith/fixed"
    config = json.loads(git("show", f"{ref}:variant.json"))
    assert f"{config['architecture']}/{config['state']}" == branch
    for path in paths:
        assert git("rev-parse", f"{ref}:{path}") == git("rev-parse", f"{base}:{path}"), (branch, path)
    files = git("ls-tree", "-r", "--name-only", ref).splitlines()
    assert not any(name.endswith("AGENTS.md") for name in files)
print("Шесть веток; README, подготовка, контракт, тесты и оценщик синхронизированы.")
