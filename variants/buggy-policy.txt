"""Шаблон исключительно учебных дефектов D01–D06; ожидаемый контракт остаётся исправным."""

import os

PRIORITIES = {"low", "normal", "high"}
STATUSES = {"new", "active", "closed"}
TRANSITIONS = {("new", "active"), ("active", "closed"), ("closed", "active")}


def enabled(code):
    """Выбрать один дефект или all; раздельное включение позволяет оценить различающую способность тестов."""
    selected = os.getenv("LAB_DEFECTS", "all").split(",")
    return "all" in selected or code in selected


def title_value(value):
    """D01 расширяет верхнюю границу до 81; контрольный тест обязан ожидать 422, а не это поведение."""
    value = value.strip()
    maximum = 81 if enabled("D01") else 80
    if not 3 <= len(value) <= maximum:
        raise ValueError("Заголовок должен содержать 3–80 символов")
    return value


def priority_value(value):
    """D02 маскирует неверный приоритет значением normal; тест проверяет код и отсутствие новой записи."""
    if value not in PRIORITIES:
        if enabled("D02"):
            return "normal"
        raise ValueError("Недопустимый приоритет")
    return value


def visible(role, user_id, author_id):
    """D03 открывает прямой доступ постороннему пользователю; проверяется отдельной второй сессией."""
    return enabled("D03") or role == "operator" or user_id == author_id


def transition_allowed(old, new):
    """D04 разрешает запрещённый new → closed; роль оператора нужна, чтобы дойти до проверки перехода."""
    return old == new or (old, new) in TRANSITIONS or (enabled("D04") and (old, new) == ("new", "closed"))


def filter_status(value):
    """D05 игнорирует фильтр: найдите лишний статус в ответе, не ограничиваясь кодом 200."""
    return None if enabled("D05") else value


def comment_author(actor_id, owner_id):
    """D06 подменяет автора комментария владельцем заявки; сравните два разных участника."""
    return owner_id if enabled("D06") else actor_id
