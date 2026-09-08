"""Небольшой сценарий чтения списка; нагрузка задаётся преподавателем."""
from locust import HttpUser, between, events, task


@events.quitting.add_listener
def check_measurements(environment, **kwargs):
    """Не допустить зелёного нагрузочного прогона без запросов или с зафиксированными ошибками."""
    if environment.stats.total.num_requests == 0 or environment.stats.total.num_failures:
        environment.process_exit_code = 1


class TicketReader(HttpUser):
    """Небольшой профиль нагрузки: вход один раз, затем чтение списка с паузами между действиями."""
    wait_time = between(0.5, 1.5)

    def on_start(self):
        """Создать сессию виртуального пользователя; тайм-аут ограничивает зависший вход."""
        response = self.client.post("/api/auth/login", json={"email": "anna@example.test", "password": "LabPassword1!"}, timeout=5)
        response.raise_for_status()
        self.client.headers["Authorization"] = "Bearer " + response.json()["access_token"]

    @task
    def list_tickets(self):
        """Измерить чтение новых заявок под постоянным именем операции в статистике Locust."""
        self.client.get("/api/tickets?status=new", name="Список новых заявок", timeout=5)
