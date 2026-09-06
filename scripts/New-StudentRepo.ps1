param([string]$Destination = 'student-work')
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskTarget = [IO.Path]::GetFullPath((Join-Path $taskRoot $Destination))
if (Test-Path -LiteralPath $taskTarget) { throw "Каталог уже существует: $taskTarget" }
New-Item -ItemType Directory -Path $taskTarget | Out-Null
Get-ChildItem -LiteralPath (Join-Path $taskRoot 'student-template') -Force | Copy-Item -Destination $taskTarget -Recurse
git -C $taskTarget init -b main
git -C $taskTarget add .
git -C $taskTarget commit -m 'Подготовлена заготовка работ по тестированию'
foreach ($taskStudent in 1..4) { git -C $taskTarget branch "student/$taskStudent" }
Write-Host "Репозиторий работ создан: $taskTarget"

