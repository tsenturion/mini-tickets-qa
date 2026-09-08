"""REST-операции заявок: права, состояния, комментарии и проверка отказа identity."""

import logging
from typing import Literal
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend import policy
from backend.config import settings
from backend.database import database
from backend.models_tickets import Comment, Ticket
from backend.schemas import CommentInput, CommentOut, StatusInput, TicketCreate, TicketOut, TicketPatch, UserOut

router = APIRouter(prefix="/api/tickets", tags=["Заявки"])
log = logging.getLogger("lab")


def remote_user(request: Request, credentials=Depends(HTTPBearer(auto_error=False))):
    """Проверить токен по HTTP с request_id и тайм-аутом; при отказе identity вернуть 503, не обходя авторизацию."""
    if credentials is None:
        raise HTTPException(401, "Нужна действующая сессия", headers={"WWW-Authenticate": "Bearer"})
    try:
        response = httpx.get(f"{settings.identity_url}/api/auth/me", headers={
            "Authorization": f"Bearer {credentials.credentials}", "X-Request-ID": request.state.request_id}, timeout=2)
        if response.status_code == 401:
            raise HTTPException(401, "Нужна действующая сессия", headers={"WWW-Authenticate": "Bearer"})
        response.raise_for_status()
        return UserOut.model_validate(response.json())
    except (httpx.HTTPError, ValueError):
        raise HTTPException(503, "Сервис пользователей недоступен") from None


if settings.service == "tickets":
    current_user = remote_user
else:
    from backend.auth import local_user as current_user


def get_ticket(ticket_id, user, db):
    """Найти доступную заявку; одинаковый 404 для отсутствующей и чужой записи не раскрывает её существование."""
    ticket = db.get(Ticket, ticket_id)
    if ticket is None or not policy.visible(user.role, user.id, ticket.author_id):
        raise HTTPException(404, "Заявка не найдена")
    return ticket


def editable(ticket, user):
    """Разрешить изменение только автору новой заявки; разделить запрет авторства 403 и состояния 409."""
    if ticket.author_id != user.id:
        raise HTTPException(403, "Изменять может только автор")
    if ticket.status != "new":
        raise HTTPException(409, "Изменять можно только новую заявку")


def save(db, entity, request, event):
    """Зафиксировать запись, перечитать серверные поля и связать изменение с запросом в журнале."""
    db.add(entity)
    db.commit()
    db.refresh(entity)
    log.info(event, extra={"fields": {"entity_id": str(entity.id), "request_id": request.state.request_id}})
    return entity


@router.get("", response_model=list[TicketOut])
def listing(status: Literal["new", "active", "closed"] | None = None, user=Depends(current_user), db: Session = Depends(database)):
    """Выдать доступные записи в фиксированном порядке и с фильтром; тесты проверяют каждый элемент."""
    query = select(Ticket)
    if user.role != "operator":
        query = query.where(Ticket.author_id == user.id)
    selected = policy.filter_status(status)
    if selected:
        query = query.where(Ticket.status == selected)
    return list(db.scalars(query.order_by(Ticket.created_at.desc(), Ticket.id.desc())))


@router.post("", status_code=201, response_model=TicketOut)
def create(body: TicketCreate, request: Request, user=Depends(current_user), db: Session = Depends(database)):
    """Создать новую заявку от текущего пользователя; сверяйте 201, defaults и фактическую запись БД."""
    return save(db, Ticket(author_id=user.id, **body.model_dump()), request, "Заявка создана")


@router.get("/{ticket_id}", response_model=TicketOut)
def detail(ticket_id: UUID, user=Depends(current_user), db: Session = Depends(database)):
    """Вернуть одну доступную заявку для проверки идентичности POST, списка и карточки."""
    return get_ticket(ticket_id, user, db)


@router.patch("/{ticket_id}", response_model=TicketOut)
def update(ticket_id: UUID, body: TicketPatch, request: Request, user=Depends(current_user), db: Session = Depends(database)):
    """Применить только переданные редактируемые поля; пустой PATCH не считается успешным изменением."""
    ticket = get_ticket(ticket_id, user, db)
    editable(ticket, user)
    fields = body.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(422, "Нужно хотя бы одно поле")
    for name, value in fields.items():
        setattr(ticket, name, value)
    return save(db, ticket, request, "Заявка изменена")


@router.delete("/{ticket_id}", status_code=204)
def remove(ticket_id: UUID, request: Request, user=Depends(current_user), db: Session = Depends(database)):
    """Удалить собственную новую заявку; через SQL проверяют каскад, через API — последующий 404."""
    ticket = get_ticket(ticket_id, user, db)
    editable(ticket, user)
    db.delete(ticket)
    db.commit()
    log.info("Заявка удалена", extra={"fields": {"entity_id": str(ticket_id), "request_id": request.state.request_id}})
    return Response(status_code=204)


@router.put("/{ticket_id}/status", response_model=TicketOut)
def change_status(ticket_id: UUID, body: StatusInput, request: Request, user=Depends(current_user), db: Session = Depends(database)):
    """Проверить роль оператора и таблицу состояний до изменения записи."""
    ticket = get_ticket(ticket_id, user, db)
    if user.role != "operator":
        raise HTTPException(403, "Статус меняет оператор")
    if not policy.transition_allowed(ticket.status, body.status):
        raise HTTPException(409, "Переход статуса запрещён")
    ticket.status = body.status
    return save(db, ticket, request, "Статус изменён")


@router.get("/{ticket_id}/comments", response_model=list[CommentOut])
def comments(ticket_id: UUID, user=Depends(current_user), db: Session = Depends(database)):
    """Вернуть комментарии доступной заявки в хронологическом порядке, включая дополнительную сортировку по ID."""
    get_ticket(ticket_id, user, db)
    return list(db.scalars(select(Comment).where(Comment.ticket_id == ticket_id).order_by(Comment.created_at, Comment.id)))


@router.post("/{ticket_id}/comments", status_code=201, response_model=CommentOut)
def add_comment(ticket_id: UUID, body: CommentInput, request: Request, user=Depends(current_user), db: Session = Depends(database)):
    """Запретить добавление в closed и записать фактического автора; этот сценарий обнаруживает D06."""
    ticket = get_ticket(ticket_id, user, db)
    if ticket.status == "closed":
        raise HTTPException(409, "Заявка закрыта")
    return save(db, Comment(ticket_id=ticket.id, author_id=policy.comment_author(user.id, ticket.author_id), text=body.text), request, "Комментарий добавлен")
