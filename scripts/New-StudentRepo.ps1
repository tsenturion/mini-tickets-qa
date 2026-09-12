<#
.SYNOPSIS
Создать личный репозиторий тестов с начальной веткой main.
.DESCRIPTION
Существующий каталог не перезаписывается. Продуктовые шесть веток не меняются;
работайте только с тестами и сохраняйте изменения коммитом перед оцениванием.
Относительный путь отсчитывается от корня продукта; абсолютный используется как есть.
Скрытые файлы CI копируются в корень работы. Удалённый репозиторий не создаётся.
.EXAMPLE
.\scripts\New-StudentRepo.ps1 -Destination C:\Users\user\repos\my-testing-work
.EXAMPLE
.\scripts\New-StudentRepo.ps1 -Destination student-work
#>
param([ValidateNotNullOrWhiteSpace()][string]$Destination = 'student-work')
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
function Invoke-GitChecked {
    <# .SYNOPSIS Не объявлять репозиторий готовым, если Git не создал коммит или ветку. #>
    param([string[]]$Arguments)
    & git @Arguments
    if ($LASTEXITCODE -ne 0) { throw 'Git не завершил создание репозитория работ' }
}
$taskTarget = [IO.Path]::GetFullPath($Destination, $taskRoot)
if (Test-Path -LiteralPath $taskTarget) { throw "Каталог уже существует: $taskTarget" }
New-Item -ItemType Directory -Path $taskTarget | Out-Null
Get-ChildItem -LiteralPath (Join-Path $taskRoot 'student-template') -Force | Copy-Item -Destination $taskTarget -Recurse
Invoke-GitChecked @('-C', $taskTarget, 'init', '-b', 'main')
Invoke-GitChecked @('-C', $taskTarget, 'add', '.')
Invoke-GitChecked @('-C', $taskTarget, 'commit', '-m', 'Подготовлена заготовка работ по тестированию')
Write-Host "Репозиторий работ создан: $taskTarget"
Write-Host 'Дальнейшие шаги: README.md в созданном каталоге — установка, публикация, CI и PR/MR.'
