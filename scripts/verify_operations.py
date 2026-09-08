"""Проверяет четыре временные среды, перезапуск, логи и отказ микросервиса.

Существующие учебные среды не используются; удаляются только тома этого прогона.
"""
from contextlib import contextmanager, ExitStack
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

import psycopg

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from grader.run import command, snapshot
from quality.support import Client
from scripts.clean_artifacts import cleanup
from scripts.runtime_directory import runtime_directory


@contextmanager
def environment(architecture, output):
    """Выделить временный Compose-проект, затем сохранить его логи и удалить только его ресурсы."""
    project = "operations-" + uuid.uuid4().hex[:10]
    destination = output / project
    destination.mkdir(parents=True)
    env = dict(os.environ, LAB_PROJECT=project, LAB_PORT="0", LAB_DB_PORT="0", LAB_DEFECTS="none")
    compose = ["docker", "compose", "-p", project]
    with runtime_directory("mini-operations") as directory:
        snapshot(f"{architecture}/fixed", directory)

        def execute(*args):
            """Выполнить Compose-команду строго с именем и окружением выделенного проверочного проекта."""
            return command(compose + list(args), cwd=directory, env=env)

        try:
            execute("up", "-d", "--build", "--wait", "--wait-timeout", "150")
            service, port = ("app", "8000") if architecture == "monolith" else ("web", "80")
            yield {"execute": execute, "url": "http://" + execute("port", service, port).strip(),
                   "db": execute("port", "db", "5432").strip(), "output": destination, "project": project}
        finally:
            result = subprocess.run(compose + ["logs", "--no-color"], cwd=directory, env=env, capture_output=True)
            (destination / "compose.log").write_bytes(result.stdout + result.stderr)
            for service in (["identity", "tickets"] if architecture == "microservices" else ["app"]):
                subprocess.run(compose + ["cp", f"{service}:/app/logs", str(destination / service)], cwd=directory, env=env, capture_output=True)
            subprocess.run(compose + ["down", "--volumes", "--remove-orphans"], cwd=directory, env=env, capture_output=True)


def entries(directory):
    """Прочитать JSON-строки скопированных журналов для проверки request_id и сохранения истории запуска."""
    return [json.loads(line) for path in directory.rglob("*.log") for line in path.read_text(encoding="utf-8").splitlines() if line.startswith("{")]


def main():
    """Доказать изоляцию четырёх сред, сохранность после рестарта и fail-closed при отказе identity."""
    cleanup(ROOT / "artifacts")
    output = ROOT / "artifacts" / ("operations-" + uuid.uuid4().hex[:10])
    output.mkdir(parents=True)
    checks = []
    print("Четыре независимые среды", flush=True)
    with ExitStack() as stack:
        environments = [stack.enter_context(environment("monolith", output)) for _ in range(4)]
        assert len({item["url"] for item in environments}) == 4
        email = "isolation-" + uuid.uuid4().hex + "@example.test"
        clients, tickets = [], []
        for number, item in enumerate(environments, start=1):
            client = Client(item["url"])
            response = client.request("POST", "/auth/register", json={"email": email, "password": "LabPassword1!"})
            assert response.status_code == 201
            client.login(email)
            clients.append(client)
            tickets.append(client.create(f"Среда студента {number}"))
        for client, ticket in zip(clients, tickets):
            assert [row["id"] for row in client.request("GET", "/tickets").json()] == [ticket["id"]]
        checks.append("Четыре одновременно работающие среды: порты, пользователи и заявки изолированы")
        item, client, ticket = environments[0], clients[0], tickets[0]
        request_id = "restart-" + uuid.uuid4().hex
        assert client.request("GET", "/tickets", headers={"X-Request-ID": request_id}).status_code == 200
        item["execute"]("restart", "app", "db")
        item["execute"]("up", "-d", "--wait", "--wait-timeout", "150")
        # Docker может назначить новый динамический порт после restart.
        client.base_url = "http://" + item["execute"]("port", "app", "8000").strip()
        assert client.request("GET", f"/tickets/{ticket['id']}").json() == ticket
        item["execute"]("cp", "app:/app/logs", str(item["output"] / "after-restart"))
        logs = entries(item["output"] / "after-restart")
        assert any(row.get("request_id") == request_id for row in logs)
        assert len({row["run_id"] for row in logs if row.get("event") == "Сервис запущен"}) == 2
        checks.append("Заявка, сессия и предыдущие логи сохранились после перезапуска приложения и БД")
        for client in clients:
            client.session.close()
    print("Отказ авторизации и изоляция баз микросервисов", flush=True)
    with environment("microservices", output) as item:
        client = Client(item["url"]).register()
        ticket = client.create("Проверка отказа зависимости")
        host, port = item["db"].rsplit(":", 1)
        for role, other in [("identity", "tickets"), ("tickets", "identity")]:
            parameters = dict(host=host, port=int(port), user=role, password=role + "-local-only", connect_timeout=3)
            with psycopg.connect(dbname=role, **parameters) as connection:
                assert connection.execute("SELECT current_database()").fetchone()[0] == role
            try:
                psycopg.connect(dbname=other, **parameters).close()
            except psycopg.OperationalError as error:
                assert "permission denied" in str(error)
            else:
                raise AssertionError("Сервис получил доступ к чужой БД")
        checks.append("Роли identity и tickets подключаются только к своим предметным базам")
        request_id = "outage-" + uuid.uuid4().hex
        assert client.request("GET", "/tickets", headers={"X-Request-ID": request_id}).status_code == 200
        item["execute"]("stop", "identity")
        response = client.request("GET", "/tickets", headers={"X-Request-ID": request_id})
        assert response.status_code == 503
        assert response.json()["error"]["request_id"] == request_id
        item["execute"]("up", "-d", "--wait", "--wait-timeout", "150")
        assert client.request("GET", f"/tickets/{ticket['id']}").status_code == 200
        for service in ["identity", "tickets"]:
            destination = item["output"] / ("check-" + service)
            item["execute"]("cp", f"{service}:/app/logs", str(destination))
            assert any(row.get("request_id") == request_id for row in entries(destination))
        ticket_logs = entries(item["output"] / "check-tickets")
        assert any(row.get("request_id") == request_id and row.get("status") == 503 for row in ticket_logs)
        checks.append("Отказ identity даёт 503; после запуска доступ восстановлен; request_id найден в логах обоих сервисов")
        client.session.close()
    (output / "result.json").write_text(json.dumps({"status": "passed", "checks": checks}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": "passed", "checks": checks, "artifacts": str(output)}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
