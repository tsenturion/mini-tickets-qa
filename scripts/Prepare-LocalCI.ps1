<#
.SYNOPSIS
Скачать и запустить локальные GitLab/Jenkins для репетиции PR/MR и pipeline.
.DESCRIPTION
Большие образы загружаются только при явном запуске этого скрипта владельцем.
Сервисы доступны на loopback; существующая PostgreSQL и основная среда не меняются.
GitLab требует существенной памяти: желательно выделить Docker не менее 12 ГБ
для одновременной работы GitLab, Jenkins и временных проверочных приложений.
.EXAMPLE
.\scripts\Prepare-LocalCI.ps1
#>
[CmdletBinding()]
param([switch]$SkipRunner)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $taskRoot

function Invoke-Checked {
    <# .SYNOPSIS Выполнить внешнюю команду и не скрыть её ненулевой код. #>
    param([scriptblock]$Action)
    & $Action
    if ($LASTEXITCODE -ne 0) { throw 'Подготовка локальных CI завершилась ошибкой' }
}

Invoke-Checked { docker info --format '{{.ServerVersion}}' }
Write-Host 'Загрузка GitLab и Jenkins может занять длительное время; скачивается несколько ГБ.'
Invoke-Checked { docker compose -f infra/ci/compose.yaml pull }
if (!$SkipRunner) {
    $taskTools = Join-Path $taskRoot '.runtime/ci-tools'
    New-Item -ItemType Directory -Path $taskTools -Force | Out-Null
    $taskRunner = Join-Path $taskTools 'gitlab-runner.exe'
    if (!(Test-Path -LiteralPath $taskRunner)) {
        Write-Host 'Загрузка GitLab Runner 19.3.0 для Windows.'
        Invoke-WebRequest -Uri 'https://gitlab-runner-downloads.s3.amazonaws.com/v19.3.0/binaries/gitlab-runner-windows-amd64.exe' -OutFile $taskRunner
    }
    Invoke-Checked { & $taskRunner --version }
}
# Повторный запуск использует прежние тома; down --volumes намеренно отсутствует.
Invoke-Checked { docker compose -f infra/ci/compose.yaml up -d --wait --wait-timeout 900 }
Write-Host 'GitLab: http://localhost:8929 ; Jenkins: http://localhost:8085'
Write-Host 'Первичная настройка и получение начальных паролей: docs/ЛОКАЛЬНЫЕ-CI.md'
Write-Host 'Не публикуйте начальные пароли, runner-токены и секрет агента в чат или Git.'
