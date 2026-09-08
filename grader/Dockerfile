# Браузеры и Python заранее установлены; версия совпадает с Playwright в lock-файле.
FROM mcr.microsoft.com/playwright/python:v1.58.0-noble@sha256:678457c4c323b981d8b4befc57b95366bb1bb6aa30057b1269f6b171e8d9975a
WORKDIR /runner
COPY requirements.txt requirements-test.txt requirements-test.lock ./
RUN pip install --no-cache-dir -r requirements-test.txt -c requirements-test.lock
COPY grader/observer.py /runner/observer.py
COPY grader/pytest.ini /runner/pytest.ini
ENV PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=/runner:/submission PYTHONUTF8=1
# Непривилегированный процесс не может менять исходники и конфигурацию оценивания.
# Кеш pytest направлен в tmpfs: /submission подключается только для чтения.
ENV PYTEST_ADDOPTS="-o cache_dir=/tmp/pytest-cache"
USER pwuser
WORKDIR /submission
ENTRYPOINT ["python", "-m", "pytest", "-c", "/runner/pytest.ini", "--rootdir=/submission", "--confcutdir=/submission", "-p", "pytest_base_url.plugin", "-p", "pytest_playwright.pytest_playwright", "-p", "pytest_timeout", "-p", "allure_pytest.plugin", "-p", "observer", "--timeout=40", "--screenshot=only-on-failure", "--tracing=retain-on-failure", "--output=/results/browser", "--junitxml=/results/junit.xml", "--alluredir=/results/allure"]
