"""Пример Page Object для входа: никакой бизнес-логики приложения и фиксированных sleep."""

class LoginPage:
    """Собрать устойчивые локаторы по подписям/ролям; assertions остаются в тестах."""
    def __init__(self, page):
        """Привязать объект страницы к отдельной Playwright Page текущего теста."""
        self.page = page

    def open(self, url):
        """Открыть внешнюю точку входа без знания архитектуры backend."""
        self.page.goto(url)

    def login(self, email, password):
        """Заполнить форму и отправить её; тест самостоятельно проверяет ожидаемый результат входа."""
        self.page.get_by_label("Email", exact=True).fill(email)
        self.page.get_by_label("Пароль", exact=True).fill(password)
        self.page.get_by_role("button", name="Войти", exact=True).click()
