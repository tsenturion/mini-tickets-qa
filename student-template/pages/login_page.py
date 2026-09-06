class LoginPage:
    def __init__(self, page):
        self.page = page

    def open(self, url):
        self.page.goto(url)

    def login(self, email, password):
        self.page.get_by_label("Email", exact=True).fill(email)
        self.page.get_by_label("Пароль", exact=True).fill(password)
        self.page.get_by_role("button", name="Войти", exact=True).click()

