"""Создаёт переносимую коллекцию без реальных паролей и токенов."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
steps = [
    ("Регистрация", "POST", "/auth/register", {"email": "{{email}}", "password": "LabPassword1!"}, 201, None),
    ("Вход", "POST", "/auth/login", {"email": "{{email}}", "password": "LabPassword1!"}, 200, "token"),
    ("Текущий пользователь", "GET", "/auth/me", None, 200, None),
    ("Создание заявки", "POST", "/tickets", {"title": "Проверка Postman", "priority": "normal"}, 201, "ticket"),
    ("Список", "GET", "/tickets?status=new", None, 200, None),
    ("Карточка", "GET", "/tickets/{{ticket}}", None, 200, None),
    ("Изменение приоритета", "PATCH", "/tickets/{{ticket}}", {"priority": "high"}, 200, None),
    ("Добавление комментария", "POST", "/tickets/{{ticket}}/comments", {"text": "Учебный комментарий"}, 201, None),
    ("Комментарии", "GET", "/tickets/{{ticket}}/comments", None, 200, None),
    ("Пользователь не меняет статус", "PUT", "/tickets/{{ticket}}/status", {"status": "active"}, 403, None),
    ("Граница 81 символ", "POST", "/tickets", {"title": "x" * 81}, 422, None),
    ("Недопустимый приоритет", "POST", "/tickets", {"title": "Проверка приоритета", "priority": "urgent"}, 422, None),
    ("Удаление заявки", "DELETE", "/tickets/{{ticket}}", None, 204, None),
    ("Удалённая заявка отсутствует", "GET", "/tickets/{{ticket}}", None, 404, None),
    ("Выход", "POST", "/auth/logout", None, 204, None),
    ("Отозванная сессия", "GET", "/auth/me", None, 401, None),
]
items = []
for name, method, path, body, status, save in steps:
    tests = [f"pm.test('Ожидаемый HTTP-код {status}', () => pm.response.to.have.status({status}));",
        "pm.test('Есть идентификатор запроса', () => pm.expect(pm.response.headers.has('X-Request-ID')).to.be.true);"]
    if save:
        tests.append(f"pm.collectionVariables.set('{save}', pm.response.json().{'access_token' if save == 'token' else 'id'});")
    request = {"method": method, "url": "{{base_url}}/api" + path,
        "header": [{"key": "Content-Type", "value": "application/json"}],
        "auth": {"type": "bearer", "bearer": [{"key": "token", "value": "{{token}}", "type": "string"}]}}
    if body:
        request["body"] = {"mode": "raw", "raw": json.dumps(body, ensure_ascii=False), "options": {"raw": {"language": "json"}}}
    item = {"name": name, "request": request, "event": [{"listen": "test", "script": {"type": "text/javascript", "exec": tests}}]}
    if name == "Регистрация":
        item["event"].append({"listen": "prerequest", "script": {"exec": ["pm.collectionVariables.set('email', 'postman-' + pm.variables.replaceIn('{{$guid}}') + '@example.test');"]}})
    items.append(item)
collection = {"info": {"name": "Мини-заявки — практикум API", "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"},
    "variable": [{"key": "base_url", "value": "http://localhost:8000"}, {"key": "token", "value": ""}, {"key": "ticket", "value": ""}], "item": items}
target = ROOT / "postman"
target.mkdir(exist_ok=True)
(target / "mini-tickets.collection.json").write_text(json.dumps(collection, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
(target / "local.environment.json").write_text(json.dumps({"name": "Локальная среда", "values": [{"key": "base_url", "value": "http://localhost:8000", "enabled": True}], "_postman_variable_scope": "environment"}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
