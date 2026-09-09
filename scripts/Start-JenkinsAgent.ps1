<#
.SYNOPSIS
Подключить Windows-исполнитель qa-windows к локальному Jenkins через WebSocket.
.DESCRIPTION
Сначала создайте узел qa-windows с меткой qa-docker и одним executor в Jenkins.
Секрет берётся с его страницы, вводится скрыто и хранится только вне Git.
Java должна быть доступна в PATH. Скрипт работает в текущем окне; Ctrl+C отключает
исполнитель, но сохраняет конфигурацию контроллера и журналы предыдущих запусков.
.EXAMPLE
.\scripts\Start-JenkinsAgent.ps1
#>
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskTools = Join-Path $taskRoot '.runtime/ci-tools'
$taskWork = Join-Path $taskTools 'jenkins-agent'
$taskLogs = Join-Path $taskTools 'logs'
New-Item -ItemType Directory -Path $taskTools, $taskWork, $taskLogs -Force | Out-Null
$taskJar = Join-Path $taskTools 'agent.jar'
$taskSecret = Join-Path $taskTools 'jenkins-agent.secret'
if (!(Test-Path -LiteralPath $taskSecret)) {
    $taskValue = Read-Host 'Секрет узла qa-windows со страницы Jenkins' -AsSecureString
    $taskCredential = [pscredential]::new('qa-windows', $taskValue)
    [IO.File]::WriteAllText($taskSecret, $taskCredential.GetNetworkCredential().Password)
    # Доступ к реквизиту ограничивается текущей учётной записью Windows и SYSTEM.
    $taskIdentity = [Security.Principal.WindowsIdentity]::GetCurrent().Name
    & icacls $taskSecret /inheritance:r /grant:r "${taskIdentity}:F" '*S-1-5-18:F' | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Не удалось ограничить доступ к секрету Jenkins' }
}
Invoke-WebRequest -Uri 'http://localhost:8085/jnlpJars/agent.jar' -OutFile $taskJar
# Очищаются только датированные журналы этого запускателя, не рабочие файлы Jenkins.
Get-ChildItem -LiteralPath $taskLogs -Filter 'jenkins-*.log' -File |
    Where-Object LastWriteTimeUtc -lt ([DateTime]::UtcNow.AddDays(-30)) |
    ForEach-Object { Remove-Item -LiteralPath $_.FullName }
$taskLog = Join-Path $taskLogs ('jenkins-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.log')
& java '-Dfile.encoding=UTF-8' -jar $taskJar -url 'http://localhost:8085/' -secret "@$taskSecret" -name 'qa-windows' -webSocket -workDir $taskWork 2>&1 | Tee-Object -FilePath $taskLog
if ($LASTEXITCODE -ne 0) { throw "CI-агент завершился с ошибкой. Журнал: $taskLog" }
