"""Authentication endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select

from app.core.audit import record_audit
from app.core.db import get_session
from app.core.deps import get_current_user
from app.core.security import create_access_token, verify_password
from app.models import User
from app.schemas import CurrentUser, LoginRequest, TokenResponse

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _authenticate(session: Session, email: str, password: str) -> User:
    user = session.exec(
        select(User).where(User.email == email, User.is_deleted == False)  # noqa: E712
    ).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if user.status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is not active")
    return user


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, session: Session = Depends(get_session)) -> TokenResponse:
    user = _authenticate(session, body.email, body.password)
    record_audit(session, action="user.login", entity="user", entity_id=user.id,
                 tenant_id=user.tenant_id, actor_id=user.id)
    session.commit()
    token = create_access_token(user.id, {"tenant_id": user.tenant_id})
    return TokenResponse(access_token=token)


@router.post("/token", response_model=TokenResponse)
def login_form(
    form: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)
) -> TokenResponse:
    """OAuth2 password flow for Swagger 'Authorize' button (username = email)."""
    user = _authenticate(session, form.username, form.password)
    token = create_access_token(user.id, {"tenant_id": user.tenant_id})
    return TokenResponse(access_token=token)


@router.get("/me", response_model=CurrentUser)
def me(current: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    return current
