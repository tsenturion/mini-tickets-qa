"""Чистые правила исправленной версии: удобный уровень для границ, таблиц решений и переходов."""

PRIORITIES = {"low", "normal", "high"}
STATUSES = {"new", "active", "closed"}
TRANSITIONS = {("new", "active"), ("active", "closed"), ("closed", "active")}


def title_value(value):
    """Обрезать края и проверить 3–80 Unicode code points; граничные значения теста — 2/3/80/81."""
    value = value.strip()
    if not 3 <= len(value) <= 80:
        raise ValueError("Заголовок должен содержать 3–80 символов")
    return value


def priority_value(value):
    """Принять только low/normal/high; неизвестное значение не должно незаметно исправляться."""
    if value not in PRIORITIES:
        raise ValueError("Недопустимый приоритет")
    return value


def visible(role, user_id, author_id):
    """Разрешить просмотр автору или оператору; остальных API должен скрыть за 404."""
    return role == "operator" or user_id == author_id


def transition_allowed(old, new):
    """Проверить таблицу переходов, включая идемпотентную повторную установку текущего статуса."""
    return old == new or (old, new) in TRANSITIONS


def filter_status(value):
    """Сохранить запрошенный статус для SQL-фильтра; проверяйте состав, а не только размер списка."""
    return value


def comment_author(actor_id, owner_id):
    """Сохранить действующего участника, не подменяя его владельцем обсуждаемой заявки."""
    return actor_id
