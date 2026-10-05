"""Стресс-профиль входов для небольшой изолированной среды с ограниченным CPU."""

from locust import HttpUser, constant, events, task
from locust.exception import StopUser


@events.quitting.add_listener
def check_measurements(environment, **kwargs):
    """Сообщить об ошибках измерения, не превращая ожидаемую деградацию в успешный прогон."""
    if (
        environment.stats.total.num_requests == 0
        or environment.stats.total.num_failures
        or (environment.runner is not None and environment.runner.exceptions)
    ):
        environment.process_exit_code = 1


class LoginStressUser(HttpUser):
    """Повторять вход, чтение собственного профиля и выход; сравнивать ступени одного сценария."""

    wait_time = constant(0.1)

    def login(self):
        """Вернуть только полученный токен; зафиксировать исходную ошибку до завершения клиента."""
        with self.client.post(
            "/api/auth/login",
            json={"email": "anna@example.test", "password": "LabPassword1!"},
            name="Вход",
            timeout=3,
            catch_response=True,
        ) as response:
            # Код 0 означает отсутствие HTTP-ответа. Оставляем исходный ReadTimeout/
            # ConnectionError в статистике Locust, вместо замены причины общим сообщением.
            if response.status_code == 0:
                return
            if response.status_code != 200:
                response.failure(f"Вход: ожидался HTTP 200, получен {response.status_code}")
                return
            try:
                token = response.json().get("access_token")
            except (ValueError, AttributeError):
                response.failure("Вход: отсутствует JSON-объект с токеном")
                return
            if not isinstance(token, str) or not token:
                response.failure("Вход: отсутствует непустой access_token")
                return
        return token

    @task
    def login_and_logout(self):
        """Завершить клиента после неудачного входа; при известном токене попытаться отозвать сессию."""
        token = self.login()
        if token is None:
            # Истёкший клиентский тайм-аут не отменяет работу сервера. Завершаем этого
            # пользователя, чтобы повторные входы не умножали ещё обрабатываемые запросы.
            # StopUser вызывается после выхода из catch_response: ошибка уже учтена.
            raise StopUser()
        headers = {"Authorization": "Bearer " + token}
        # После тайм-аута входа сервер может позднее сохранить сессию, токен которой
        # клиент не получил. Такие записи останутся только в отдельной учебной БД.
        try:
            with self.client.get(
                "/api/auth/me",
                headers=headers,
                name="Свой профиль",
                timeout=3,
                catch_response=True,
            ) as response:
                if response.status_code not in {0, 200}:
                    response.failure(f"Профиль: ожидался HTTP 200, получен {response.status_code}")
                elif response.status_code == 200:
                    try:
                        if response.json().get("email") != "anna@example.test":
                            response.failure("Профиль: email не соответствует вошедшему пользователю")
                    except (ValueError, AttributeError):
                        response.failure("Профиль: отсутствует корректный JSON-объект")
        finally:
            with self.client.post(
                "/api/auth/logout",
                headers=headers,
                name="Выход",
                timeout=3,
                catch_response=True,
            ) as response:
                if response.status_code not in {0, 204}:
                    response.failure(f"Выход: ожидался HTTP 204, получен {response.status_code}")
