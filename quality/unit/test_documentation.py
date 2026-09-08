"""Защитить учебные пояснения от случайной потери при следующем изменении кода."""
from scripts.check_documentation import missing_docstrings


def test_all_python_has_documentation():
    """Каждый авторский модуль, класс и функция, включая вложенные, имеют docstring."""
    assert missing_docstrings() == []
