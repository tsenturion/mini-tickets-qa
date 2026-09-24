<#
.SYNOPSIS
Подключить локальный Windows-агент Jenkins с читаемым русским журналом.
.DESCRIPTION
Секрет читается Java непосредственно из файла внутри .runtime; скрипт его не выводит.
Окно PowerShell остаётся занятым до остановки агента сочетанием Ctrl+C.
#>
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskJar = Join-Path $taskRoot '.runtime/ci-tools/agent.jar'
$taskSecret = Join-Path $taskRoot '.runtime/ci-tools/jenkins-agent.secret'
$taskWork = Join-Path $taskRoot '.runtime/jenkins'
if (!(Test-Path -LiteralPath $taskJar)) { throw 'Сначала скачайте agent.jar по инструкции docs/ЛОКАЛЬНЫЕ-CI.md.' }
if (!(Test-Path -LiteralPath $taskSecret)) { throw 'Сначала сохраните секрет узла в .runtime/ci-tools/jenkins-agent.secret.' }
New-Item -ItemType Directory -Path $taskWork -Force | Out-Null

# Java выводит журнал в UTF-8; PowerShell должен декодировать тот же поток как UTF-8.
# Одна только опция -Dfile.encoding у Java не меняет кодовую страницу терминала.
$taskUtf8 = [Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = $taskUtf8
$OutputEncoding = $taskUtf8
if ($IsWindows) { chcp.com 65001 > $null }

& java '-Dfile.encoding=UTF-8' '-Dstdout.encoding=UTF-8' '-Dstderr.encoding=UTF-8' `
    -jar $taskJar -url 'http://localhost:8085/' -secret "@$taskSecret" `
    -name 'qa-windows' -webSocket -workDir $taskWork
if ($LASTEXITCODE -ne 0) { throw "Агент Jenkins завершился с кодом $LASTEXITCODE." }
