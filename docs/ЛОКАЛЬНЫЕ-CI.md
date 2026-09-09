# Локальные GitLab и Jenkins

Эта инфраструктура отделена от минимального приложения. GitLab/Jenkins нужны для учебной интеграционной приёмки, но не для модулей UI/API/SQL. Официальные образы закреплены версиями и digest; большие загрузки запускает владелец:

```powershell
.\scripts\Prepare-LocalCI.ps1
.\scripts\Prepare-LocalCI.ps1 -JenkinsPlugins
```

GitLab доступен на `http://localhost:8929`, Jenkins — на `http://localhost:8085`. Это новые локальные установки: пароли удалённого стенда к ним не относятся. Если эти порты уже заняты вашей установкой, не останавливайте её вслепую: используйте существующий сервис или измените порты этого Compose-проекта.

Для GitLab ориентируйтесь минимум на 8 ГБ памяти, а для всей репетиции — на 12 ГБ и более, выделенных Docker. Это не требование маленького приложения, а стоимость GitLab. Источники: [требования GitLab](https://docs.gitlab.com/install/requirements/), [Docker-установка GitLab](https://docs.gitlab.com/install/docker/installation/), [Docker-установка Jenkins](https://www.jenkins.io/doc/book/installing/docker/).

## Первичная настройка

Начальный пароль GitLab для пользователя root можно посмотреть локально:

```powershell
docker compose -f infra/ci/compose.yaml exec gitlab cat /etc/gitlab/initial_root_password
```

Войдите и смените пароль. Начальный файл не предназначен для постоянного хранения. Создайте приватные проекты продукта и работ; их ветки остаются раздельными. Не включайте публичный доступ к учебным секретам.

Начальный пароль мастера Jenkins:

```powershell
docker compose -f infra/ci/compose.yaml exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

Ключ `-JenkinsPlugins` устанавливает Pipeline, Git, JUnit и Timestamper с зависимостями и перезапускает только учебный Jenkins. Перед повторной установкой дождитесь окончания заданий. После установки откройте мастер, пропустите дополнительные плагины и настройте администратора. Для Multibranch с PR/MR дополнительно нужен соответствующий GitHub/GitLab Branch Source. Учётные данные репозиториев настраиваются в Credentials, не вставляются в Jenkinsfile. Команды [управления плагинами](https://www.jenkins.io/doc/book/managing/plugins/) не заменяют настройку пользователей и прав.

## Почему агенты на Windows

Контроллеры работают в Docker, а shell-runner GitLab и агент Jenkins — на этой машине/учебном Windows-стенде. Это повторяет установленный Python/Node/Git и избегает вложенного Docker. Docker socket контроллеру Jenkins не подключён. На агенте используются отдельные рабочие каталоги и виртуальные Python-среды.

GitLab Runner скачивается в `.runtime/ci-tools/gitlab-runner.exe`. В настройках приватного проекта создайте runner с тегом `qa-docker`. Зарегистрируйте его командой `gitlab-runner.exe register`, указав URL `http://localhost:8929`, выданный authentication token, executor `shell` и shell `pwsh`. Токен вводится локально; конфигурацию храните в игнорируемом каталоге `.runtime`, а не в репозитории.

Для Jenkins создайте постоянный агент `qa-windows` с меткой `qa-docker`, одним executor и отдельным Remote root directory. Выберите запуск inbound agent через WebSocket. Команду скачивания agent.jar и запуска возьмите со страницы созданного агента; используйте установленный совместимый JDK. Не передавайте секрет агента студентам.

Разместите весь проект в коротком Windows-пути **без кириллицы**, например `C:\Users\user\repos\testing`. Для Remote root directory укажите полный путь к `.runtime/jenkins` внутри проекта. Иначе служебный bat-файл `GIT_ASKPASS` Git-плагина может не запуститься, и клонирование приватного репозитория завершится ошибкой авторизации. После смены Remote root directory переподключите агент: подключённый Jenkins кеширует прежний путь.

Сохраните секрет с его страницы без отображения ввода, ограничив доступ к файлу:

```powershell
New-Item -ItemType Directory -Path .runtime/ci-tools -Force | Out-Null
$taskSecret = Read-Host 'Секрет узла qa-windows' -AsSecureString
$taskCredential = [pscredential]::new('qa-windows', $taskSecret)
$taskSecretPath = Join-Path (Get-Location) '.runtime/ci-tools/jenkins-agent.secret'
[IO.File]::WriteAllText($taskSecretPath, $taskCredential.GetNetworkCredential().Password)
$taskAccount = [Security.Principal.WindowsIdentity]::GetCurrent().Name
icacls $taskSecretPath /inheritance:r /grant:r "${taskAccount}:F" '*S-1-5-18:F'
Remove-Variable taskSecret, taskCredential
Invoke-WebRequest http://localhost:8085/jnlpJars/agent.jar -OutFile .runtime/ci-tools/agent.jar
[Console]::OutputEncoding = [Text.UTF8Encoding]::new()
java '-Dfile.encoding=UTF-8' '-Dstdout.encoding=UTF-8' '-Dstderr.encoding=UTF-8' -jar .runtime/ci-tools/agent.jar -url http://localhost:8085/ -secret '@.runtime/ci-tools/jenkins-agent.secret' -name qa-windows -webSocket -workDir .runtime/jenkins
```

После `Connected` оставьте окно открытым. Секрет передаётся через файл, не через аргументы процесса. При его перевыпуске повторите сохранение. `INFO` в stderr Java — служебный журнал, а не признак неуспешного подключения. Журналы remoting сохраняются в `.runtime/jenkins/remoting`; при обслуживании удаляйте только его `*.log*` старше 30 дней, не каталог целиком. Логи и артефакты заданий ограничены 30 днями в Jenkinsfile.

Пример регистрации runner с конфигурацией вне Git (токен вводится интерактивно):

```powershell
$taskCIRoot = Join-Path (Get-Location) '.runtime/gl'
.\.runtime\ci-tools\gitlab-runner.exe register --config .runtime/ci-tools/config.toml --template-config infra/ci/runner-template.toml --url http://localhost:8929 --executor shell --shell pwsh --builds-dir "$taskCIRoot/builds" --cache-dir "$taskCIRoot/cache"
.\.runtime\ci-tools\gitlab-runner.exe run --config .runtime/ci-tools/config.toml
```

Вторая команда работает, пока открыто окно PowerShell. Сервис Windows можно настроить
позже отдельно; для первой репетиции это не требуется. Jenkins `--wait` подтверждает
запуск контейнера, но до открытия мастера может понадобиться дополнительное время.

Служебные checkout-каталоги CI находятся внутри `.runtime` проекта и не входят в Git. На Windows длинный путь до временного Git-снимка или отчёта может приводить к `Input/output error` внутри Docker Desktop: каталог существует на хосте, но недоступен в контейнере. Поэтому важны короткий латинский путь проекта и шаблон регистрации `infra/ci/runner-template.toml`. Он включает `custom_build_dir` и задаёт `GIT_CLONE_PATH=$CI_BUILDS_DIR/$CI_CONCURRENT_ID/$CI_PROJECT_ID`: разные проекты и параллельные слоты не используют один checkout.

Для уже зарегистрированного runner добавьте `GIT_CLONE_PATH` в массив `environment` его секции `[[runners]]` и включите `[runners.custom_build_dir]` по образцу шаблона. Сохраните имеющиеся переменные, токен и URL; повторная регистрация не нужна. При переносе поправьте также `builds_dir` и `cache_dir`. Новые задания возьмут новые каталоги после перечитывания конфигурации runner. Предварительная проверка оценщика возвращает для недоступного mount `infrastructure_error`, а не «пустую работу».

Shell-runner имеет полномочия пользователя Windows и доступ к Docker. На нём разрешены только доверенные pipelines преподавателя. Код сдаваемой работы исполняется контейнерным оценщиком без Docker socket; защита задания/ветки на стороне GitLab/Jenkins обязательна.

## Проверка после настройки

### Доступ к приватному продукту из GitLab MR

В проекте продукта откройте Settings → CI/CD → Job token permissions и добавьте **только проект работ** в allowlist. Пользователю, запускающему MR, нужны права чтения продукта. В проекте работ задайте CI/CD variables `QA_PRODUCT_URL` (например `http://localhost:8929/root/mini-tickets-qa.git`) и `QA_PRODUCT_REF` (полный доверенный SHA продукта). Это не пароли; они должны быть доступны в учебной исходной ветке MR, а не только в protected-ветках.

`student-template/ci_grade.py` использует временный `CI_JOB_TOKEN` только для клонирования с того же сервера. Токен не сохраняется в адресе remote или аргументах Git; переходы на другой URL запрещены. Удалённому серверу нужен HTTPS, HTTP разрешён только на loopback. Персональный токен администратора для такой проверки не требуется. См. [права job token](https://docs.gitlab.com/ci/jobs/ci_job_token/).

Глубина Git-клона в обоих `.gitlab-ci.yml` равна `0`: старые коммиты закреплённого выпуска должны быть доступны. В Settings → CI/CD → Artifacts отключите Keep artifacts from most recent successful jobs, иначе срок `expire_in: 30 days` не ограничит хранение последнего успешного результата.

### Задания Jenkins

В Manage Jenkins → Nodes создайте Windows-агент с меткой `qa-docker`, а число executors встроенного узла установите в `0`. Создайте Pipeline с Definition → Pipeline script from SCM, Git-адресом продукта, Credentials для чтения и Script Path `Jenkinsfile`. Для оценивания создайте второе такое задание с Script Path `ci/grading.Jenkinsfile`, закрепив доверенный SHA продукта. Передайте ему `SUBMISSION_URL`, `SUBMISSION_SHA` и при необходимости `SUBMISSION_CREDENTIALS_ID`; значение этого параметра — идентификатор Credentials, не пароль.

Продукт и работа могут использовать разные токены чтения одного GitLab. Jenkinsfile перед checkout создаёт локальный Git-каталог и отключает `credential.helper` только в нём: Git получает выбранные Jenkins Credentials через `GIT_ASKPASS`, не обращаясь к кешу паролей Windows. Глобальные настройки Git на компьютере не изменяются. При `HTTP Basic: Access denied` проверьте права и срок действия именно токена нужного проекта, затем выбранный `credentialsId`.

При выборе **точного SHA**, а не имени ветки, снимите флажок Lightweight checkout: Git-плагин при облегчённом чтении может принять SHA за имя ветки и запросить несуществующий `refs/heads/<SHA>`. Обычный checkout получает историю и выбирает нужный коммит. В самом задании также включите Discard old builds → 30 дней: это ограничит хранение даже при отказе до чтения Jenkinsfile.

В обоих заданиях используйте адрес `http://localhost:8929/root/mini-tickets-qa.git`, для работы — адрес соответствующего проекта с тем же хостом. `Prepare-LocalCI.ps1` настраивает правило Git **только внутри контроллера Jenkins**, чтобы такой адрес превращался в `http://gitlab:8929/` в сети Docker. На Windows он остаётся localhost. Системный Git Windows и DNS не меняются. Для уже работающих контейнеров достаточно одной команды без повторных загрузок:

```powershell
docker compose -f infra/ci/compose.yaml exec -T jenkins git config --global url.http://gitlab:8929/.insteadOf http://localhost:8929/
```

Не запускайте изменяемый YAML работы на общем shell-runner без предварительного ревью. Для итоговой оценки используйте доверенное задание Jenkins. Pipeline работы нужен как учебный пример интеграции, а не как защищённый источник правил зачёта.

1. Загрузить все шесть продуктовых веток и отдельный репозиторий работ.
2. Запустить `ci/verify.py` через GitLab pipeline и продуктовый Jenkinsfile.
3. Создать настоящий MR в репозитории работ. Зафиксировать исходный SHA.
4. Проверить этот SHA через доверенный `ci/grading.Jenkinsfile` и демонстрационный GitLab pipeline. Сравнить grade.json, не только зелёный/красный индикатор.
5. Повторить с хорошими тестами, постоянным падением и пустой работой. Ошибку Docker проверить отдельно: она должна стать infrastructure_error, а не обнаруженным дефектом.
6. Проверить JUnit, логи, trace, ограничения доступа и 30-дневное хранение. В GitLab отключить бессрочное сохранение артефактов последнего успешного pipeline; в Jenkins не ставить «хранить навсегда».

До выполнения этих шагов локальные CI нельзя считать проверенными. Запущенный контейнер и корректный YAML ещё не доказывают работоспособность PR/MR.

## Остановка без потери данных

```powershell
docker compose -f infra/ci/compose.yaml stop
docker compose -f infra/ci/compose.yaml start
```

Репозитории, конфигурация и логи находятся в именованных томах. Не используйте down --volumes для обычной остановки. Pipeline-артефакты хранятся не более 30 дней; внутренние служебные журналы контроллеров также требуют регулярного обслуживания.
