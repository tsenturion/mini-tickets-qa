PRIORITIES = {"low", "normal", "high"}
STATUSES = {"new", "active", "closed"}
TRANSITIONS = {("new", "active"), ("active", "closed"), ("closed", "active")}


def title_value(value):
    value = value.strip()
    if not 3 <= len(value) <= 80:
        raise ValueError("Заголовок должен содержать 3–80 символов")
    return value


def priority_value(value):
    if value not in PRIORITIES:
        raise ValueError("Недопустимый приоритет")
    return value


def visible(role, user_id, author_id):
    return role == "operator" or user_id == author_id


def transition_allowed(old, new):
    return old == new or (old, new) in TRANSITIONS


def filter_status(value):
    return value


def comment_author(actor_id, owner_id):
    return actor_id

