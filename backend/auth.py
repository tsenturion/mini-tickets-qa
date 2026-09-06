import hashlib
import logging
import secrets
from datetime import timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import database
from backend.models_identity import LoginSession, User, utcnow
from backend.schemas import Credentials, TokenOut, UserOut

router = APIRouter(prefix="/api/auth", tags=["Авторизация"])
bearer = HTTPBearer(auto_error=False)
hasher = PasswordHasher()
dummy_hash = hasher.hash("Отсутствующий пользователь")
log = logging.getLogger("lab")


def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def unauthorized():
    return HTTPException(401, "Нужна действующая сессия", headers={"WWW-Authenticate": "Bearer"})


def local_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(database)):
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized()
    session = db.get(LoginSession, digest(credentials.credentials))
    if not session or session.expires_at <= utcnow():
        raise unauthorized()
    user = db.get(User, session.user_id)
    if not user:
        raise unauthorized()
    return UserOut.model_validate(user)


@router.post("/register", status_code=201, response_model=UserOut)
def register(body: Credentials, request: Request, db: Session = Depends(database)):
    user = User(email=body.email, password_hash=hasher.hash(body.password), role="user")
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Email уже зарегистрирован") from None
    db.refresh(user)
    log.info("Пользователь зарегистрирован", extra={"fields": {"user_id": str(user.id), "request_id": request.state.request_id}})
    return user


@router.post("/login", response_model=TokenOut)
def login(body: Credentials, response: Response, db: Session = Depends(database)):
    user = db.scalar(select(User).where(User.email == body.email))
    try:
        verified = hasher.verify(user.password_hash if user else dummy_hash, body.password)
    except (VerificationError, InvalidHashError):
        verified = False
    if not verified or not user:
        raise unauthorized()
    token = secrets.token_urlsafe(32)
    db.execute(delete(LoginSession).where(LoginSession.expires_at <= utcnow()))
    db.add(LoginSession(token_hash=digest(token), user_id=user.id, expires_at=utcnow() + timedelta(seconds=settings.session_seconds)))
    db.commit()
    response.headers["Cache-Control"] = "no-store"
    return TokenOut(access_token=token, expires_in=settings.session_seconds)


@router.get("/me", response_model=UserOut)
def me(user: UserOut = Depends(local_user)):
    return user


@router.post("/logout", status_code=204)
def logout(user: UserOut = Depends(local_user), credentials=Depends(bearer), db: Session = Depends(database)):
    db.execute(delete(LoginSession).where(LoginSession.token_hash == digest(credentials.credentials)))
    db.commit()
    return Response(status_code=204)

