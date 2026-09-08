"""Временные каталоги стенда с наследуемыми правами для Docker Desktop.

Python 3.13 ограничивает Windows ACL при mkdir(mode=0o700), в том числе
в tempfile.TemporaryDirectory. Docker работает от другого контекста доступа.
Используем отдельный игнорируемый каталог проекта, не меняя права системного Temp.
"""
from contextlib import contextmanager
from pathlib import Path
import shutil
import stat
import uuid

ROOT = Path(__file__).resolve().parents[1]


@contextmanager
def runtime_directory(prefix, base=None):
    """Выдать уникальный каталог прогона и удалить только его после выхода.

Наследование ACL сохраняет доступ Docker; секреты CI сюда не копируются.
Параметр base используется тестами, чтобы проверять очистку в собственной среде.
"""
    parent = (Path(base) if base is not None else ROOT / ".runtime/runs").resolve()
    parent.mkdir(parents=True, exist_ok=True)
    if not prefix.replace("-", "").isalnum():
        raise ValueError("Префикс временного каталога должен быть простым именем")
    directory = parent / (prefix + "-" + uuid.uuid4().hex)
    directory.mkdir(mode=0o777)
    try:
        yield directory
    finally:
        # Не разрешаем очистке выйти за пределы конкретного выделенного каталога.
        if directory.is_symlink() or directory.resolve().parent != parent:
            raise RuntimeError("Путь временного каталога изменён; автоматическая очистка остановлена")
        def remove_readonly(function, filename, error):
            """Снять read-only только с собственного временного файла Git и повторить удаление.

Остальные ошибки не скрываются: занятой файл или иной отказ доступа требует диагностики.
"""
            path = Path(filename)
            if (not isinstance(error, PermissionError) or path.is_symlink()
                    or not path.resolve().is_relative_to(directory.resolve())
                    or not path.is_file() or path.stat().st_mode & stat.S_IWRITE):
                raise error
            # Git делает объекты read-only; Windows запрещает unlink до снятия атрибута.
            path.chmod(stat.S_IREAD | stat.S_IWRITE)
            function(filename)

        shutil.rmtree(directory, onexc=remove_readonly)
