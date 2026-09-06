FROM mcr.microsoft.com/playwright/python:v1.58.0-noble
WORKDIR /runner
COPY requirements.txt requirements-test.txt requirements-test.lock ./
RUN pip install --no-cache-dir -r requirements-test.txt -c requirements-test.lock
COPY grader/observer.py /runner/observer.py
COPY grader/pytest.ini /runner/pytest.ini
ENV PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=/runner:/submission PYTHONUTF8=1
USER pwuser
WORKDIR /submission
ENTRYPOINT ["python", "-m", "pytest", "-c", "/runner/pytest.ini", "-p", "pytest_base_url.plugin", "-p", "pytest_playwright.pytest_playwright", "-p", "pytest_timeout", "-p", "allure_pytest.plugin", "-p", "observer", "--timeout=40", "--screenshot=only-on-failure", "--tracing=retain-on-failure", "--output=/results/browser", "--junitxml=/results/junit.xml", "--alluredir=/results/allure"]
