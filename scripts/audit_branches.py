"""Проверка количества вариантов и синхронности общих учебных материалов."""
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
expected = {f"{architecture}/{state}" for architecture in ["monolith", "client-server", "microservices"] for state in ["fixed", "buggy"]}


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True, encoding="utf-8").strip()


actual = set(git("for-each-ref", "--format=%(refname:short)", "refs/heads").splitlines())
if actual != expected:
    raise SystemExit(f"Ожидалось шесть веток: {sorted(expected)}; найдено: {sorted(actual)}")
paths = ["contract/openapi.json", "docs/ТРЕБОВАНИЯ.md", "docs/ПРАКТИКУМ.md", "grader/result.py", "grader/observer.py",
         "ci/verify.py", "quality/api/test_defects.py", "quality/ui/test_interface.py", "frontend/src/App.vue", "requirements.lock", "requirements-test.lock"]
for branch in sorted(expected):
    config = json.loads(git("show", f"{branch}:variant.json"))
    assert f"{config['architecture']}/{config['state']}" == branch
    for path in paths:
        assert git("rev-parse", f"{branch}:{path}") == git("rev-parse", f"monolith/fixed:{path}"), (branch, path)
    files = git("ls-tree", "-r", "--name-only", branch).splitlines()
    assert not any(name.endswith("AGENTS.md") for name in files)
print("Шесть веток; контракт, тесты и оценщик синхронизированы; AGENTS.md не отслеживается.")

