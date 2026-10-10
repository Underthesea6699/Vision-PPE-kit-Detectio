import hashlib
import re

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth import (
    SESSION_COOKIE_NAME,
    SESSION_DURATION,
    create_session,
    get_current_user,
    get_db,
    hash_password,
    verify_password,
)
from app.models.user import User, UserSession


router = APIRouter(prefix="/api/auth", tags=["Authentication"])


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)


def normalize_email(email: str) -> str:
    normalized = email.strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Enter a valid email address.",
        )
    return normalized


def set_session_cookie(response: Response, token: str, request: Request) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=int(SESSION_DURATION.total_seconds()),
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="lax",
        path="/",
    )


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(
    request_body: RegisterRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    email = normalize_email(request_body.email)
    name = request_body.name.strip()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Enter your name.",
        )

    user = User(
        name=name,
        email=email,
        password_hash=hash_password(request_body.password),
    )
    db.add(user)

    try:
        db.flush()
        token = create_session(db, user)
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        ) from error

    set_session_cookie(response, token, request)
    return {
        "message": "Account created successfully.",
        "user": {"name": user.name, "email": user.email},
    }


@router.post("/login")
def login(
    request_body: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    email = normalize_email(request_body.email)
    user = db.query(User).filter(User.email == email).first()
    password_hash = user.password_hash if user else (
        "pbkdf2_sha256$600000$00000000000000000000000000000000$"
        "0000000000000000000000000000000000000000000000000000000000000000"
    )

    if user is None or not verify_password(request_body.password, password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email or password is incorrect.",
        )

    token = create_session(db, user)
    db.commit()
    set_session_cookie(response, token, request)
    return {
        "message": "Signed in successfully.",
        "user": {"name": user.name, "email": user.email},
    }


@router.get("/me")
def current_user(user: User = Depends(get_current_user)):
    return {"name": user.name, "email": user.email}


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token:
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        db.query(UserSession).filter(UserSession.token_hash == token_hash).delete()
        db.commit()

    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="lax",
        path="/",
    )
    return {"message": "Signed out successfully."}
