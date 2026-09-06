"""Небольшой сценарий чтения списка; нагрузка задаётся преподавателем."""
from locust import HttpUser, between, task


class TicketReader(HttpUser):
    wait_time = between(0.5, 1.5)

    def on_start(self):
        response = self.client.post("/api/auth/login", json={"email": "anna@example.test", "password": "LabPassword1!"})
        response.raise_for_status()
        self.client.headers["Authorization"] = "Bearer " + response.json()["access_token"]

    @task
    def list_tickets(self):
        self.client.get("/api/tickets?status=new", name="Список новых заявок")
