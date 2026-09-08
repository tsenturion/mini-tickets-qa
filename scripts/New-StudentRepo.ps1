<#
.SYNOPSIS
Создать отдельный репозиторий тестов с main и четырьмя студенческими ветками.
.DESCRIPTION
Существующий каталог не перезаписывается. Продуктовые шесть веток не меняются;
студенты работают только с тестами и сохраняют изменения коммитом перед оцениванием.
#>
param([string]$Destination = 'student-work')
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
function Invoke-GitChecked {
    <# .SYNOPSIS Не объявлять репозиторий готовым, если Git не создал коммит или ветку. #>
    param([string[]]$Arguments)
    & git @Arguments
    if ($LASTEXITCODE -ne 0) { throw 'Git не завершил создание репозитория работ' }
}
$taskTarget = [IO.Path]::GetFullPath((Join-Path $taskRoot $Destination))
if (Test-Path -LiteralPath $taskTarget) { throw "Каталог уже существует: $taskTarget" }
New-Item -ItemType Directory -Path $taskTarget | Out-Null
Get-ChildItem -LiteralPath (Join-Path $taskRoot 'student-template') -Force | Copy-Item -Destination $taskTarget -Recurse
Invoke-GitChecked @('-C', $taskTarget, 'init', '-b', 'main')
Invoke-GitChecked @('-C', $taskTarget, 'add', '.')
Invoke-GitChecked @('-C', $taskTarget, 'commit', '-m', 'Подготовлена заготовка работ по тестированию')
foreach ($taskStudent in 1..4) { Invoke-GitChecked @('-C', $taskTarget, 'branch', "student/$taskStudent") }
Write-Host "Репозиторий работ создан: $taskTarget"
