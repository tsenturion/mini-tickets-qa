"""Адаптер демонстрационного MR; итоговый доверенный запуск настраивает преподаватель."""
import os
from pathlib import Path
import subprocess
import sys

product = Path("product")
subprocess.run(["git", "clone", os.environ["QA_PRODUCT_URL"], str(product)], check=True)
subprocess.run(["git", "checkout", "--detach", os.environ["QA_PRODUCT_REF"]], cwd=product, check=True)
subprocess.run(["docker", "build", "-f", "grader/Dockerfile", "-t", "mini-tickets-grader:1.0", "."], cwd=product, check=True)
subprocess.run([sys.executable, "scripts/freeze_release.py"], cwd=product, check=True)
raise SystemExit(subprocess.call([sys.executable, "grader/run.py", "--submission", "..", "--refs", "artifacts/release-lock.json"], cwd=product))

