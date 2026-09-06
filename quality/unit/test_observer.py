import json
import os
from pathlib import Path
import subprocess
import sys


def test_observer_distinguishes_call_setup_and_skip(tmp_path):
    sample = tmp_path / "test_sample.py"
    sample.write_text("""import pytest
@pytest.mark.api
@pytest.mark.requirement('TICKET-01')
def test_assertion():
    assert False
@pytest.fixture
def broken():
    raise RuntimeError('ошибка подготовки')
def test_setup(broken):
    pass
@pytest.mark.skip(reason='учебный пример')
def test_skip():
    pass
""", encoding="utf-8")
    destination = tmp_path / "result.json"
    root = Path(__file__).resolve().parents[2]
    env = dict(os.environ, PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", OBSERVER_REPORT=str(destination), PYTHONPATH=str(root))
    process = subprocess.run([sys.executable, "-m", "pytest", "-c", str(root / "grader/pytest.ini"), "--rootdir", str(tmp_path),
        "-p", "grader.observer", str(sample), "-q"], env=env, cwd=tmp_path, capture_output=True)
    assert process.returncode == 1, (process.stdout + process.stderr).decode("utf-8", errors="replace")
    cases = json.loads(destination.read_text(encoding="utf-8"))["cases"]
    by_name = {key.split("::")[-1]: value for key, value in cases.items()}
    assert by_name["test_assertion"]["assertion"]
    assert by_name["test_setup"]["outcome"] == "error"
    assert by_name["test_skip"]["outcome"] == "skipped"
    subprocess.run([sys.executable, "-m", "pytest", "-c", str(root / "grader/pytest.ini"), "--rootdir", str(tmp_path),
        "-p", "grader.observer", str(sample), "-k", "test_assertion", "-q"], env=env, cwd=tmp_path, capture_output=True)
    filtered = json.loads(destination.read_text(encoding="utf-8"))["cases"]
    assert len(filtered) == 1
