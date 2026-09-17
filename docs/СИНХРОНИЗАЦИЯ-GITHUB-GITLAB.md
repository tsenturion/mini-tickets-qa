# Синхронизация GitHub и GitLab

Один локальный Git-репозиторий может быть связан сразу с GitHub и локальным
GitLab. В этой схеме `origin` указывает на GitHub, а `gitlab` — на GitLab. Git
передаёт между площадками коммиты, ветки и теги; настройки CI, runners,
variables, PR, MR, issues и артефакты настраиваются отдельно на каждой площадке.

Автоматическое двустороннее зеркало для учебной работы не используется: если
одна ветка независимо меняется на двух площадках, синхронизация может получить
два разных продолжения истории. Для каждого изменения сначала выберите
площадку, на которой выполняется merge, а затем перенесите получившийся коммит
на вторую площадку.

## Первичный импорт из GitHub в GitLab

Сначала убедитесь, что исходный репозиторий полностью опубликован в GitHub. Для
продукта источником является:

```text
https://github.com/tsenturion/mini-tickets-qa.git
```

Для личного репозитория тестов используйте его собственный GitHub Clone URL.
Затем в GitLab выполните следующие действия:

1. Выберите `Create new → New project/repository → Import project`.
2. Выберите `Repository by URL`.
3. Укажите GitHub Clone URL в поле `Git repository URL`.
4. Выберите namespace и задайте `Project name` и `Project slug`.
5. Если источник требует аутентификацию, используйте токен с правом чтения
   репозитория вместо пароля учётной записи.
6. Нажмите `Create project` и дождитесь завершения импорта.

Если пункта `Repository by URL` нет, администратор GitLab должен открыть
`Admin → Settings → General → Import and export settings`, включить источник
`Repository by URL` и сохранить настройку. Возможность и состав импорта описаны
в [официальной инструкции GitLab](https://docs.gitlab.com/user/import/third_party_systems/repo_by_url/).

Импорт через Git URL переносит Git-историю, ветки и теги, но не переносит PR,
MR, issues, настройки CI/CD и выпуски как объекты интерфейса. После импорта
настройте variables, runner и правила доступа уже в созданном GitLab-проекте.

Для продукта проверьте наличие шести веток и тега выпуска:

```powershell
$taskGitLabProduct = 'http://localhost:8929/root/mini-tickets-qa.git'
git ls-remote --heads $taskGitLabProduct
git ls-remote --tags $taskGitLabProduct
```

Ожидаемые продуктовые ветки:

- `monolith/fixed`;
- `monolith/buggy`;
- `client-server/fixed`;
- `client-server/buggy`;
- `microservices/fixed`;
- `microservices/buggy`.

Если проект с нужным путём уже существует, повторный импорт не создавайте.
Обновите его из GitHub по следующему разделу.

## Настройка двух remote

В локальном клоне сохраните понятные имена площадок:

```powershell
git remote -v
git remote add gitlab http://localhost:8929/root/mini-tickets-qa.git
git remote -v
```

Для личного репозитория замените путь `root/mini-tickets-qa` на namespace и имя
своего проекта. Если remote `gitlab` уже существует, проверьте или исправьте его
адрес:

```powershell
git remote get-url gitlab
git remote set-url gitlab http://localhost:8929/YOUR_NAMESPACE/YOUR_PROJECT.git
```

Команды `git remote` меняют только локальную конфигурацию `.git/config` и не
попадают в коммиты.

## Обновление GitLab после изменений в GitHub

Сначала получите актуальное состояние GitHub:

```powershell
git fetch origin --prune --tags
```

Для личного репозитория передайте нужные ветки и теги явно:

```powershell
git push gitlab refs/remotes/origin/main:refs/heads/main
git push gitlab refs/remotes/origin/practice/02-ci:refs/heads/practice/02-ci
git push gitlab --tags
```

Для продукта синхронизируйте все шесть архитектурных веток:

```powershell
$taskProductBranches = @(
    'monolith/fixed',
    'monolith/buggy',
    'client-server/fixed',
    'client-server/buggy',
    'microservices/fixed',
    'microservices/buggy'
)

git fetch origin --prune --tags
foreach ($taskBranch in $taskProductBranches) {
    git push gitlab "refs/remotes/origin/${taskBranch}:refs/heads/${taskBranch}"
}
git push gitlab --tags
```

Такой способ не удаляет дополнительные ветки GitLab. `git push --mirror`
перезаписывает весь набор refs и может удалить отсутствующие в источнике ветки,
поэтому он подходит только для контролируемого первичного переноса в пустой
проект, а не для повседневной учебной работы.

Сравните SHA на обеих площадках:

```powershell
$taskBranch = 'monolith/fixed'
git ls-remote origin "refs/heads/$taskBranch"
git ls-remote gitlab "refs/heads/$taskBranch"
```

Совпадающий SHA означает, что обе площадки получили один Git-коммит. Он не
означает, что на них автоматически появились одинаковые PR/MR или настройки CI.

## Один коммит для PR и MR

Рабочую ветку отправляйте из одного локального клона на обе площадки:

```powershell
$taskBranch = 'practice/02-ci'
git push -u origin $taskBranch
git push -u gitlab $taskBranch
git rev-parse HEAD
```

Откройте PR и MR из этой ветки в `main` и сравните SHA исходной ветки. Новый
локальный коммит снова отправьте на оба remote — открытые PR/MR обновятся.

Не объединяйте PR и MR независимо, если требуется сохранить полностью
одинаковую историю `main`: две площадки могут создать разные merge-коммиты.
Выберите одну площадку для merge и перенесите получившийся `main` на вторую.

## Перенос результата из GitLab в GitHub

После merge в GitLab получите итоговый коммит и сначала просмотрите расхождение:

```powershell
git fetch gitlab --prune --tags
git fetch origin --prune --tags
git log --oneline --graph --decorate --max-count=20 `
    origin/main gitlab/main
```

Если `gitlab/main` является прямым продолжением `origin/main`, перенесите его в
GitHub:

```powershell
git push origin refs/remotes/gitlab/main:refs/heads/main
git push origin --tags
```

Если правила GitHub не разрешают прямое обновление `main`, создайте ветку
синхронизации и откройте PR:

```powershell
git switch --create sync/gitlab-main gitlab/main
git push -u origin sync/gitlab-main
```

После merge этого PR обновите локальный `main` обычным `git fetch` и
`git pull --ff-only`.

Если обе версии `main` содержат уникальные коммиты, не используйте force push.
Создайте отдельную интеграционную ветку, объедините изменения с просмотром diff,
проверьте результат и передайте его через PR/MR.

## Перенос результата из GitHub в GitLab

После merge в GitHub выполните обратную операцию:

```powershell
git fetch origin --prune --tags
git fetch gitlab --prune --tags
git log --oneline --graph --decorate --max-count=20 `
    origin/main gitlab/main
git push gitlab refs/remotes/origin/main:refs/heads/main
git push gitlab --tags
```

При запрете прямого обновления `main` создайте в GitLab ветку синхронизации и
откройте MR. Перед каждой передачей проверяйте направление и точные refs в
команде: слева находится источник, справа — назначение.

## Проверка перед продолжением работы

```powershell
git status --short --branch
git remote -v
git fetch origin --prune --tags
git fetch gitlab --prune --tags
git log --oneline --graph --decorate --all --max-count=30
```

Перед новой практической работой убедитесь, что выбранный `main` начинается с
ожидаемого коммита, а рабочая ветка создаётся от него. Для запуска GitHub Actions
и GitLab CI на одном содержимом отправляйте один и тот же локальный SHA на обе
площадки.
