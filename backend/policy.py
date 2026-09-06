import os

PRIORITIES = {"low", "normal", "high"}
STATUSES = {"new", "active", "closed"}
TRANSITIONS = {("new", "active"), ("active", "closed"), ("closed", "active")}


def enabled(code):
    selected = os.getenv("LAB_DEFECTS", "all").split(",")
    return "all" in selected or code in selected


def title_value(value):
    value = value.strip()
    maximum = 81 if enabled("D01") else 80
    if not 3 <= len(value) <= maximum:
        raise ValueError("Заголовок должен содержать 3–80 символов")
    return value


def priority_value(value):
    if value not in PRIORITIES:
        if enabled("D02"):
            return "normal"
        raise ValueError("Недопустимый приоритет")
    return value


def visible(role, user_id, author_id):
    return enabled("D03") or role == "operator" or user_id == author_id


def transition_allowed(old, new):
    return old == new or (old, new) in TRANSITIONS or (enabled("D04") and (old, new) == ("new", "closed"))


def filter_status(value):
    return None if enabled("D05") else value


def comment_author(actor_id, owner_id):
    return owner_id if enabled("D06") else actor_id

