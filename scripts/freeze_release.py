"""Фиксирует шесть коммитов для одинакового оценивания работ."""
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
result = {}
for architecture in ["monolith", "client-server", "microservices"]:
    for state in ["fixed", "buggy"]:
        branch = f"{architecture}/{state}"
        process = subprocess.run(["git", "rev-parse", "--verify", branch], cwd=ROOT, capture_output=True, text=True)
        if process.returncode:
            process = subprocess.run(["git", "rev-parse", "--verify", f"origin/{branch}"], cwd=ROOT, capture_output=True, text=True, check=True)
        result[branch] = process.stdout.strip()
target = ROOT / "artifacts/release-lock.json"
target.parent.mkdir(exist_ok=True)
target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(target)

