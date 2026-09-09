<#
.SYNOPSIS
Подготовить приложение и тестовый инструментарий без изменения глобального Python.
.DESCRIPTION
Browsers устанавливает локальные браузеры для доверенных тестов. Grader собирает
большой изолированный контейнер для кода студента. Обычному приложению он не нужен.
.EXAMPLE
.\scripts\Prepare-Lab.ps1 -Browsers -Grader
#>
param([switch]$Grader, [switch]$Browsers)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $taskRoot
function Invoke-Checked {
    <# .SYNOPSIS Сохранить ненулевой код внешней команды и остановить подготовку при первой ошибке. #>
    param([scriptblock]$Action)
    & $Action
    if ($LASTEXITCODE -ne 0) { throw 'Команда подготовки завершилась ошибкой' }
}
Write-Host 'Подготовка зависимостей. Первый запуск скачивает образы и пакеты.'
Invoke-Checked { docker version }
if (!(Test-Path -LiteralPath '.venv')) { Invoke-Checked { python -m venv .venv } }
# Изолируем зависимости от глобального Python, не удаляя среду и чужие установки.
$taskVenvConfig = Join-Path $taskRoot '.venv/pyvenv.cfg'
if ((Get-Content -LiteralPath $taskVenvConfig -Raw) -match 'include-system-site-packages = true') {
    Invoke-Checked { python -m venv .venv }
}
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
