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
.EXAMPLE
.\scripts\Prepare-LocalCI.ps1 -JenkinsPlugins
#>
[CmdletBinding()]
param([switch]$SkipRunner, [switch]$JenkinsPlugins)
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
# Для Windows localhost — хост, для Jenkins в Docker — сам контейнер.
# Правило относится только к Git внутри учебного контроллера и сохраняется в его томе.
Invoke-Checked { docker compose -f infra/ci/compose.yaml exec -T jenkins git config --global url.http://gitlab:8929/.insteadOf http://localhost:8929/ }
if ($JenkinsPlugins) {
    # Явный ключ разрешает установку и перезапуск только учебного контроллера.
    # Перед повторным запуском дождитесь завершения заданий Jenkins.
    Write-Host 'Установка Pipeline, Git, JUnit и Timestamper с зависимостями; затем перезапуск Jenkins.'
    Invoke-Checked { docker compose -f infra/ci/compose.yaml exec -T jenkins jenkins-plugin-cli --plugins workflow-aggregator:608.v67378e9d3db_1 git:5.10.1 junit:1425.v9c7318dca_96d timestamper:1.30 --plugin-download-directory /var/jenkins_home/plugins }
    Invoke-Checked { docker compose -f infra/ci/compose.yaml restart jenkins }
}
Write-Host 'GitLab: http://localhost:8929 ; Jenkins: http://localhost:8085'
Write-Host 'Первичная настройка и получение начальных паролей: docs/ЛОКАЛЬНЫЕ-CI.md'
Write-Host 'Не публикуйте начальные пароли, runner-токены и секрет CI-агента в Git, отчётах или переписке.'
