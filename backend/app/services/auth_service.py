"""Logica de autenticacion. No conoce HTTP: lanza AuthError, no HTTPException."""

from sqlmodel import Session

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.models.user import User
from app.repositories import user_repository
from app.schemas.auth import TokenResponse


class AuthError(Exception):
    """Error de dominio para fallos de autenticacion."""


def authenticate(session: Session, email: str, password: str) -> User:
    user = user_repository.get_by_email(session, email)
    if user is None or not verify_password(password, user.hashed_password):
        raise AuthError("Credenciales invalidas")
    if not user.is_active:
        raise AuthError("Usuario inactivo")
    return user


def _tokens_for(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(str(user.id), user.role.value),
        refresh_token=create_refresh_token(str(user.id), user.role.value),
    )


def login(session: Session, email: str, password: str) -> TokenResponse:
    user = authenticate(session, email, password)
    return _tokens_for(user)


def refresh(session: Session, refresh_token: str) -> TokenResponse:
    payload = decode_token(refresh_token, "refresh")
    if payload is None:
        raise AuthError("Refresh token invalido o expirado")
    user = user_repository.get_by_id(session, int(payload["sub"]))
    if user is None or not user.is_active:
        raise AuthError("Usuario no encontrado o inactivo")
    return _tokens_for(user)
