"""Acceso a datos de usuarios. Solo queries; sin logica de negocio."""

from sqlmodel import Session, select

from app.models.user import User, UserRole


def get_by_email(session: Session, email: str) -> User | None:
    return session.exec(select(User).where(User.email == email)).first()


def get_by_id(session: Session, user_id: int) -> User | None:
    return session.get(User, user_id)


def create(
    session: Session,
    *,
    email: str,
    full_name: str,
    hashed_password: str,
    role: UserRole,
) -> User:
    user = User(
        email=email,
        full_name=full_name,
        hashed_password=hashed_password,
        role=role,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user
