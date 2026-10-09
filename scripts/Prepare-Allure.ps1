#Requires -Version 7.0

<#
.SYNOPSIS
Подготавливает локальный Allure CLI 2.46.1 и показывает команды для отчёта.

.DESCRIPTION
Проверяет npm.cmd и java.exe, устанавливает CLI только в .runtime проекта и не меняет системные переменные.

.EXAMPLE
./scripts/Prepare-Allure.ps1 -ResultsDirectory 'artifacts/allure/run-01' -ReportDirectory 'artifacts/allure-report/run-01'
#>
[CmdletBinding()]
param(
    [string]$ResultsDirectory = 'artifacts/allure',
    [string]$ReportDirectory = 'artifacts/allure-report'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$expectedVersion = '2.46.1'
$projectRoot = Split-Path -Parent $PSScriptRoot
$installDirectory = [System.IO.Path]::GetFullPath((Join-Path $projectRoot '.runtime/allure-cli'))
$allureCommand = Join-Path $installDirectory 'node_modules/.bin/allure.cmd'
$resultsPath = if ([System.IO.Path]::IsPathFullyQualified($ResultsDirectory)) {
    [System.IO.Path]::GetFullPath($ResultsDirectory)
} else {
    [System.IO.Path]::GetFullPath((Join-Path $projectRoot $ResultsDirectory))
}
$reportPath = if ([System.IO.Path]::IsPathFullyQualified($ReportDirectory)) {
    [System.IO.Path]::GetFullPath($ReportDirectory)
} else {
    [System.IO.Path]::GetFullPath((Join-Path $projectRoot $ReportDirectory))
}

function Get-AllureVersion {
    <#
    .SYNOPSIS
    Возвращает версию исправного локального Allure CLI или null при невозможности запуска.
    #>
    if (-not (Test-Path -LiteralPath $allureCommand -PathType Leaf)) {
        return $null
    }

    $versionOutput = & $allureCommand --version 2>$null
    if ($LASTEXITCODE -ne 0) {
        return $null
    }
    return ($versionOutput | Out-String).Trim()
}

Write-Host "Проверяю локальный Allure CLI в $installDirectory"
$installedVersion = Get-AllureVersion
if ($installedVersion -eq $expectedVersion) {
    Write-Host "Allure CLI $expectedVersion уже установлен и исправен. Повторная загрузка не требуется."
}
else {
    $npm = Get-Command npm.cmd -ErrorAction SilentlyContinue
    $java = Get-Command java.exe -ErrorAction SilentlyContinue
    if (-not $npm -or -not $java) {
        throw 'Для подготовки Allure CLI требуются npm.cmd и java.exe, доступные через PATH.'
    }

    Write-Host "Устанавливаю Allure CLI $expectedVersion локально, без изменения системных PATH и JAVA_HOME."
    & $npm.Source install `
        --prefix $installDirectory `
        --no-save `
        --package-lock=false `
        --ignore-scripts `
        --no-audit `
        --no-fund `
        --registry https://registry.npmjs.org `
        "allure-commandline@$expectedVersion"
    if ($LASTEXITCODE -ne 0) {
        throw "npm завершил установку Allure CLI с кодом $LASTEXITCODE."
    }

    Write-Host 'Проверяю установленный локальный CLI.'
    $installedVersion = Get-AllureVersion
    if ($installedVersion -ne $expectedVersion) {
        throw "Ожидалась версия Allure CLI $expectedVersion, получена '$installedVersion'."
    }
    Write-Host "Allure CLI $installedVersion подготовлен успешно."
}

Write-Host 'Для формирования и открытия отчёта выполните:'
Write-Host "& '$allureCommand' generate '$resultsPath' -o '$reportPath'"
Write-Host "& '$allureCommand' open '$reportPath' --host 127.0.0.1"
