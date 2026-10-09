# Подготовка и очистка тестового набора

Используйте единую базу `lab` варианта `monolith/fixed`. Скрипты создают отдельного
пользователя, его новую заявку с приоритетом `high` и один комментарий. Пользователь
получает учебный пароль `LabPassword1!`: корректный Argon2-хеш копируется внутри
PostgreSQL из записи `anna@example.test`, без вывода значения.

Откройте PowerShell 7 в корне проекта с запущенными `app` и `db`. Подготовьте
кодировку и новые идентификаторы набора:

```powershell
$ErrorActionPreference = 'Stop'
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$dataUserId = [guid]::NewGuid().ToString()
$dataTicketId = [guid]::NewGuid().ToString()
$dataCommentId = [guid]::NewGuid().ToString()
$dataEmail = "sql-$dataUserId@example.test"
```

Сохраните эти значения до завершения очистки: каждый файл получает тот же набор.
Для следующей независимой проверки создайте новые UUID.

## Создание

```powershell
Get-Content -LiteralPath sql/test-data/prepare.sql -Raw -Encoding UTF8 |
    docker compose exec -T -e PGCLIENTENCODING=UTF8 db psql -X -U lab -d lab `
        -v "user_id=$dataUserId" -v "ticket_id=$dataTicketId" `
        -v "comment_id=$dataCommentId"
if ($LASTEXITCODE -ne 0) { throw 'Подготовка данных завершилась ошибкой' }
```

Это предпросмотр: `RETURNING` покажет созданные строки, а `ROLLBACK` отменит их.
Для сохранения добавьте к этому вызову `psql` параметр `-v persist=true`.
Скрипт сохраняет весь связанный набор одной транзакцией. Повторная подготовка с
уже сохранёнными UUID даст ошибку уникальности и не изменит существующий набор.

## Проверка

```powershell
Get-Content -LiteralPath sql/test-data/inspect.sql -Raw -Encoding UTF8 |
    docker compose exec -T -e PGCLIENTENCODING=UTF8 db psql -X -U lab -d lab `
        -v "user_id=$dataUserId" -v "ticket_id=$dataTicketId" `
        -v "comment_id=$dataCommentId"
if ($LASTEXITCODE -ne 0) { throw 'Проверка данных завершилась ошибкой' }
```

После сохранённой подготовки ожидайте по одной строке пользователя, заявки и
комментария. Счётчик сессий сначала равен нулю, затем увеличивается при входе
через API. Email для входа хранится в `$dataEmail`; UUID заявки — в
`$dataTicketId`. После отката подготовки все четыре счётчика равны нулю.

## Очистка

```powershell
Get-Content -LiteralPath sql/test-data/cleanup.sql -Raw -Encoding UTF8 |
    docker compose exec -T -e PGCLIENTENCODING=UTF8 db psql -X -U lab -d lab `
        -v "user_id=$dataUserId" -v "ticket_id=$dataTicketId" `
        -v "comment_id=$dataCommentId"
if ($LASTEXITCODE -ne 0) { throw 'Очистка данных завершилась ошибкой' }
```

Это также предпросмотр с `ROLLBACK`. Сверьте кандидатов и строки `RETURNING` с
UUID своего набора. Для подтверждения повторите вызов с `-v persist=true`,
затем отдельно выполните `inspect.sql`: все счётчики должны стать нулевыми.
Само сообщение о завершении скрипта подтверждает выполнение, а не отсутствие
остаточных данных. Удаление пользователя каскадно удаляет его сессии.

Каждый пример запускает новый `psql`; файл включает `ON_ERROR_STOP`. При SQL-
ошибке клиент завершится, а незавершённая транзакция откатится при закрытии
соединения. Если открыли файл через `\i` в постоянной интерактивной консоли,
после ошибки завершите транзакцию командой `ROLLBACK` перед продолжением.

Шаблоны и публичные параметры подходят для сохранения в репозитории работ.
Пароли, хеши и значения токенов в вывод скриптов и диагностические материалы
не входят. Прямой SQL подготавливает исходное состояние; он не заменяет
проверки бизнес-правил через API.
