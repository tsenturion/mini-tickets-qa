"""Проверка текущей продуктовой ветки; одинаковый вход для трёх CI.

Скрипт разделяет три исхода: функциональное несоответствие продукта, корректно
обнаруженные учебные дефекты buggy-варианта и невозможность подготовить среду.
Это различие сохраняется в ``result.json`` и коде завершения, чтобы случайный
сбой Docker или сбора тестов не выглядел как найденный дефект.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.clean_artifacts import cleanup


def main():
    """Проверить текущую ветку в чистой среде; у buggy отдельно подтвердить ровно восемь ожидаемых падений."""
    # Общий artifacts не очищается целиком: helper удаляет только файлы старше
    # 30 дней и проверяет, что путь относится к разрешённому диагностическому
    # каталогу. Новый запуск пишет в отдельный каталог ниже.
    cleanup(ROOT / "artifacts")
    variant = json.loads((ROOT / "variant.json").read_text())

    # Уникальное Compose-имя является границей одного запуска: контейнеры,
    # сеть и тома не пересекаются с другой сборкой. Нулевые host-порты просят
    # Docker выбрать свободные значения, поэтому параллельные задания разных
    # веток не конкурируют за заранее заданные порты.
    project = "verify-" + uuid.uuid4().hex[:10]
    output = ROOT / "artifacts" / project
    output.mkdir(parents=True)
    env = dict(os.environ, LAB_PROJECT=project, LAB_PORT="0", LAB_DB_PORT="0", LAB_DEFECTS="all", PYTHONUTF8="1")
    compose = ["docker", "compose", "-p", project]

    # В монолите HTTP-входом является само приложение, в остальных
    # архитектурах — Nginx. BASE_URL всегда указывает на публичную границу,
    # чтобы проверки не обходили маршрутизацию клиент-серверного варианта или
    # gateway микросервисов.
    service, port = ("app", "8000") if variant["architecture"] == "monolith" else ("web", "80")
    failed = False
    try:
        subprocess.run(compose + ["up", "-d", "--build", "--wait", "--wait-timeout", "150"], cwd=ROOT, env=env, check=True)
        binding = subprocess.check_output(compose + ["port", service, port], cwd=ROOT, env=env, text=True).strip()
        env["BASE_URL"] = "http://" + binding
        env["ARTIFACT_DIR"] = str(output / "console")

        # Обычный прогон buggy-варианта проверяет работоспособность вокруг
        # известных мутаций: проверки самих D01–D08 выполняются ниже отдельно.
        # Иначе ожидаемые assertion-падения сделали бы продуктовый pipeline
        # красным ещё до проверки того, что это именно нужные дефекты.
        groups = ["quality/unit", "quality/api/test_contract.py", "quality/ui"]
        if variant["state"] == "buggy":
            groups += ["--ignore=quality/unit/test_policy.py", "-k", "not test_d07 and not test_d08"]
        else:
            groups += ["quality/api/test_defects.py"]

        # SQL-набор описывает единую схему lab и прямую реляционную границу.
        # В микросервисах данные разделены между identity и tickets, поэтому их
        # целостность проверяется через сервисные контракты, а не этим набором.
        if variant["architecture"] != "microservices":
            db_binding = subprocess.check_output(compose + ["port", "db", "5432"], cwd=ROOT, env=env, text=True).strip()
            env["SQL_DATABASE_URL"] = "postgresql://lab:" + env.get("LAB_DB_PASSWORD", "lab-local-only") + "@" + db_binding + "/lab"
            groups += ["quality/sql"]
        # JUnit используется CI как машинный итог, Allure — для разбора шагов,
        # а screenshot/trace создаются только при падении и сохраняют контекст
        # браузера без постоянного разрастания успешных артефактов.
        code = subprocess.call([sys.executable, "scripts/check.py", *groups, "--junitxml=" + str(output / "tests.xml"),
            "--alluredir=" + str(output / "allure"), "--screenshot=only-on-failure", "--tracing=retain-on-failure", "--output=" + str(output / "browser")], cwd=ROOT, env=env)
        # Функциональный отказ запоминается, но не прерывает buggy-прогон:
        # отдельное подтверждение мутаций даёт дополнительную диагностику и не
        # должно теряться из-за более раннего красного набора.
        failed |= code != 0
        if variant["state"] == "buggy":
            env["OBSERVER_REPORT"] = str(output / "defects.json")
            code = subprocess.call([sys.executable, "scripts/check.py", "quality/api/test_defects.py", "quality/ui/test_interface.py", "-k", "test_d0",
                "-p", "grader.observer", "--junitxml=" + str(output / "expected-defects.xml")], cwd=ROOT, env=env)
            observed = json.loads((output / "defects.json").read_text(encoding="utf-8"))

            # Код 1 здесь ожидаем: восемь тестов должны упасть именно в фазе
            # assertion. Точное количество, outcome и непустой текст assertion
            # не позволяют принять collection/setup error или общий отказ
            # приложения за успешное подтверждение учебных мутаций.
            confirmed = code == 1 and len(observed["cases"]) == 8 and all(case["outcome"] == "failed" and case["assertion"] for case in observed["cases"].values())
            failed |= not confirmed
            print("Восемь ожидаемых дефектов подтверждены:", confirmed)
        # result.json — компактный контракт для CI-обвязки; детальная причина
        # остаётся в JUnit, Allure, browser artifacts и compose.log.
        (output / "result.json").write_text(json.dumps({"status": "failed" if failed else "passed", "variant": variant}, ensure_ascii=False), encoding="utf-8")
        return int(failed)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as error:
        # Ошибки запуска Compose и системных команд имеют отдельный код 2.
        # Ненулевой код самих тестов обрабатывается выше как результат проверки
        # и не смешивается с невозможностью подготовить инфраструктуру.
        (output / "result.json").write_text(json.dumps({"status": "infrastructure_error", "reason": str(error)}, ensure_ascii=False), encoding="utf-8")
        print("Среда не позволила проверить стенд:", str(error), file=sys.stderr)
        return 2
    finally:
        # Диагностика снимается до teardown, пока контейнеры и их файловые
        # системы доступны. Копирование логов best-effort: его код не заменяет
        # уже установленный результат проверки. После этого удаляются только
        # ресурсы уникального Compose-проекта данного запуска, включая тома с
        # тестовыми данными и возможные orphan-контейнеры.
        result = subprocess.run(compose + ["logs", "--no-color"], cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
        (output / "compose.log").write_text(result.stdout + result.stderr, encoding="utf-8")
        for app in (["identity", "tickets"] if variant["architecture"] == "microservices" else ["app"]):
            subprocess.run(compose + ["cp", f"{app}:/app/logs", str(output / f"logs-{app}")], cwd=ROOT, env=env, capture_output=True)
        subprocess.run(compose + ["down", "--volumes", "--remove-orphans"], cwd=ROOT, env=env)


if __name__ == "__main__":
    raise SystemExit(main())
