"""Фиксирует шесть коммитов для одинакового оценивания работ."""
import json
import argparse
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--current", action="store_true", help="Вместо выпуска взять текущие вершины веток для подготовки следующего выпуска")
args = parser.parse_args()
result = {}
for architecture in ["monolith", "client-server", "microservices"]:
    for state in ["fixed", "buggy"]:
        branch = f"{architecture}/{state}"
        if args.current:
            process = subprocess.run(["git", "rev-parse", "--verify", branch], cwd=ROOT, capture_output=True, text=True)
            if process.returncode:
                process = subprocess.run(["git", "rev-parse", "--verify", f"origin/{branch}"], cwd=ROOT, capture_output=True, text=True, check=True)
        else:
            release = json.loads((ROOT / "releases/1.0.0.json").read_text(encoding="utf-8"))
            process = subprocess.run(["git", "rev-parse", "--verify", release[branch] + "^{commit}"], cwd=ROOT, capture_output=True, text=True, check=True)
        result[branch] = process.stdout.strip()
target = ROOT / "artifacts/release-lock.json"
target.parent.mkdir(exist_ok=True)
target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(target)
