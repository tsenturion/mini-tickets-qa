# Браузеры и Python заранее установлены; версия совпадает с Playwright в lock-файле.
FROM mcr.microsoft.com/playwright/python:v1.58.0-noble@sha256:678457c4c323b981d8b4befc57b95366bb1bb6aa30057b1269f6b171e8d9975a
WORKDIR /runner
COPY requirements.txt requirements-test.txt requirements-test.lock ./
RUN pip install --no-cache-dir -r requirements-test.txt -c requirements-test.lock
COPY grader/observer.py /runner/observer.py
COPY grader/pytest.ini /runner/pytest.ini
COPY grader/entrypoint.py /runner/entrypoint.py
ENV PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=/runner:/submission PYTHONUTF8=1
# Непривилегированный процесс не может менять исходники и конфигурацию оценивания.
# Кеш pytest направлен в tmpfs: /submission подключается только для чтения.
ENV PYTEST_ADDOPTS="-o cache_dir=/tmp/pytest-cache"
USER pwuser
# Старт вне bind mount позволяет зарегистрировать даже отказ доступа к /submission.
WORKDIR /runner
ENTRYPOINT ["python", "/runner/entrypoint.py"]
