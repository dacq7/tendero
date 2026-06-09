"""Dependencias de autenticacion y autorizacion para los endpoints."""

from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session

from app.core.security import decode_token
from app.db.session import get_session
from app.models.user import User, UserRole
from app.repositories import user_repository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

_credentials_exc = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="No autenticado",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session),
) -> User:
    payload = decode_token(token, "access")
    if payload is None:
        raise _credentials_exc
    user = user_repository.get_by_id(session, int(payload["sub"]))
    if user is None or not user.is_active:
        raise _credentials_exc
    return user


def require_role(*roles: UserRole) -> Callable[[User], User]:
    """Factory: devuelve una dependencia que exige uno de los roles dados."""

    def _guard(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para esta accion",
            )
        return current_user

    return _guard
