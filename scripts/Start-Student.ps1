param([ValidateRange(1,4)][int]$Student = 1)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
$env:LAB_PROJECT = "mini-student-$Student"
$env:LAB_PORT = [string](8100 + $Student)
$env:LAB_DB_PORT = [string](55440 + $Student)
docker compose up -d --build --wait
if ($LASTEXITCODE -ne 0) { throw 'Не удалось запустить среду студента' }
Write-Host "Студент $Student — http://localhost:$env:LAB_PORT ; PostgreSQL localhost:$env:LAB_DB_PORT"

