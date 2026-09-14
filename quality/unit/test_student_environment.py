"""Проверяет выбор независимой среды без запуска Docker."""

from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[2]
POWERSHELL = shutil.which("pwsh")
pytestmark = pytest.mark.skipif(not POWERSHELL, reason="Для проверки сценария нужен PowerShell 7")


def run_script(arguments: str) -> subprocess.CompletedProcess[str]:
    """Подменить только команду Docker и вернуть рассчитанные сценарием переменные."""
    path = (ROOT / "scripts/Start-Student.ps1").as_posix().replace("'", "''")
    command = (
        "function docker { $global:LASTEXITCODE = 0 }; "
        f"& '{path}' {arguments}; "
        "Write-Output ($env:LAB_PROJECT + '|' + $env:LAB_PORT + '|' + $env:LAB_DB_PORT)"
    )
    return subprocess.run([POWERSHELL, "-NoProfile", "-NonInteractive", "-Command", command],
        capture_output=True, text=True, encoding="utf-8", timeout=15)


@pytest.mark.parametrize("arguments,expected", [
    ("-Student 27", "mini-student-27|8127|55467"),
    ("-Student 310 -HttpPort 9200 -DbPort 59200", "mini-student-310|9200|59200"),
])
def test_arbitrary_number_and_explicit_ports(arguments, expected):
    """Номер не ограничен составом группы, а занятые порты можно заменить явно."""
    result = run_script(arguments)
    assert result.returncode == 0, result.stdout + result.stderr
    assert expected in result.stdout.splitlines()
