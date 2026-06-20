"""Auth + RBAC dependencies (NFR-001 tenant isolation, NFR-002 RBAC enforcement)."""
from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, select

from app.core.db import get_session
from app.core.security import decode_access_token
from app.models import Role, RolePermission, User, UserRole
from app.schemas import CurrentUser

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=True)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session),
) -> CurrentUser:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
    except Exception:  # noqa: BLE001
        raise credentials_error
    if not user_id:
        raise credentials_error

    user = session.get(User, user_id)
    if not user or user.is_deleted or user.status != "active":
        raise credentials_error

    role_ids = session.exec(select(UserRole.role_id).where(UserRole.user_id == user.id)).all()
    role_names: list[str] = []
    permissions: set[str] = set()
    for rid in role_ids:
        role = session.get(Role, rid)
        if role:
            role_names.append(role.name)
        for code in session.exec(
            select(RolePermission.permission_code).where(RolePermission.role_id == rid)
        ).all():
            permissions.add(code)

    return CurrentUser(
        id=user.id,
        tenant_id=user.tenant_id,
        email=user.email,
        full_name=user.full_name,
        roles=role_names,
        permissions=sorted(permissions),
    )


def require_permission(code: str):
    """Dependency factory enforcing a permission code (wildcard '*' allowed)."""

    def checker(current: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if "*" in current.permissions or code in current.permissions:
            return current
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Missing required permission: {code}",
        )

    return checker
