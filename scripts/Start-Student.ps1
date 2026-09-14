<#
.SYNOPSIS
Запустить независимую среду по уникальному номеру на предсказуемых портах.
.DESCRIPTION
Имена Compose-проектов разделяют тома и сети. Переменные LAB_* остаются в текущем
PowerShell, поэтому docker compose stop в этом окне остановит именно эту среду.
Архитектура и состояние берутся из текущей продуктовой ветки, а не из номера студента.
.PARAMETER Student
Уникальный положительный номер среды. По умолчанию добавляется к базовым портам.
.PARAMETER HttpPort
HTTP-порт приложения. Ноль выбирает 8100 + номер среды.
.PARAMETER DbPort
Порт PostgreSQL. Ноль выбирает 55440 + номер среды.
#>
param(
    [ValidateRange(1,10000)][int]$Student = 1,
    [ValidateRange(0,65535)][int]$HttpPort = 0,
    [ValidateRange(0,65535)][int]$DbPort = 0
)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
$env:LAB_PROJECT = "mini-student-$Student"
$env:LAB_PORT = [string]$(if ($HttpPort) { $HttpPort } else { 8100 + $Student })
$env:LAB_DB_PORT = [string]$(if ($DbPort) { $DbPort } else { 55440 + $Student })
if ($env:LAB_PORT -eq $env:LAB_DB_PORT) { throw 'HTTP и PostgreSQL должны использовать разные порты' }
docker compose up -d --build --wait
if ($LASTEXITCODE -ne 0) { throw 'Не удалось запустить среду студента' }
Write-Host "Среда $Student — http://localhost:$env:LAB_PORT ; PostgreSQL localhost:$env:LAB_DB_PORT"
