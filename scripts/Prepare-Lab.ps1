param([switch]$Grader, [switch]$Browsers)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $taskRoot
function Invoke-Checked { param([scriptblock]$Action) & $Action; if ($LASTEXITCODE -ne 0) { throw 'Команда подготовки завершилась ошибкой' } }
Write-Host 'Подготовка зависимостей. Первый запуск скачивает образы и пакеты.'
Invoke-Checked { docker version }
if (!(Test-Path -LiteralPath '.venv')) { Invoke-Checked { python -m venv .venv } }
Invoke-Checked { & '.\.venv\Scripts\python.exe' -m pip install -r requirements-test.txt -c requirements-test.lock }
Push-Location frontend
try { Invoke-Checked { npm ci }; Invoke-Checked { npm run build } } finally { Pop-Location }
Invoke-Checked { docker compose build }
if ($Browsers) { Invoke-Checked { & '.\.venv\Scripts\python.exe' -m playwright install chromium firefox webkit } }
if ($Grader) {
    Write-Host 'Образ оценщика с браузерами большой. Дождитесь завершения загрузки.'
    Invoke-Checked { docker build -f grader/Dockerfile -t mini-tickets-grader:1.0 . }
}
Write-Host 'Подготовка завершена. Запуск приложения: docker compose up -d --wait'
