# Локальные GitLab и Jenkins

Эта инфраструктура отделена от минимального приложения. GitLab/Jenkins нужны для учебной интеграционной приёмки, но не для модулей UI/API/SQL. Официальные образы закреплены версиями и digest; большие загрузки запускает владелец:

```powershell
.\scripts\Prepare-LocalCI.ps1
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

Откройте мастер, установите рекомендуемые плагины, создайте своего администратора. Для имеющихся Jenkinsfile требуются Pipeline, Git, JUnit и Timestamper; для Multibranch с PR/MR — соответствующий GitHub/GitLab Branch Source. Учётные данные репозиториев настраиваются в Credentials, не вставляются в Jenkinsfile.

## Почему агенты на Windows

Контроллеры работают в Docker, а shell-runner GitLab и агент Jenkins — на этой машине/учебном Windows-стенде. Это повторяет установленный Python/Node/Git и избегает вложенного Docker. Docker socket контроллеру Jenkins не подключён. На агенте используются отдельные рабочие каталоги и виртуальные Python-среды.

GitLab Runner скачивается в `.runtime/ci-tools/gitlab-runner.exe`. В настройках приватного проекта создайте runner с тегом `qa-docker`. Зарегистрируйте его командой `gitlab-runner.exe register`, указав URL `http://localhost:8929`, выданный authentication token, executor `shell` и shell `pwsh`. Токен вводится локально; конфигурацию храните в игнорируемом каталоге `.runtime`, а не в репозитории.

Для Jenkins создайте постоянный агент `qa-windows` с меткой `qa-docker`, одним executor и отдельным Remote root directory. Выберите запуск inbound agent через WebSocket. Команду скачивания agent.jar и запуска возьмите со страницы созданного агента; используйте установленный совместимый JDK. Не передавайте секрет агента студентам.

Пример регистрации runner с конфигурацией вне Git (токен вводится интерактивно):

```powershell
.\.runtime\ci-tools\gitlab-runner.exe register --config .runtime/ci-tools/config.toml --url http://localhost:8929 --executor shell --shell pwsh
.\.runtime\ci-tools\gitlab-runner.exe run --config .runtime/ci-tools/config.toml
```

Вторая команда работает, пока открыто окно PowerShell. Сервис Windows можно настроить
позже отдельно; для первой репетиции это не требуется. Jenkins `--wait` подтверждает
запуск контейнера, но до открытия мастера может понадобиться дополнительное время.

Shell-runner имеет полномочия пользователя Windows и доступ к Docker. На нём разрешены только доверенные pipelines преподавателя. Код сдаваемой работы исполняется контейнерным оценщиком без Docker socket; защита задания/ветки на стороне GitLab/Jenkins обязательна.

## Проверка после настройки

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
