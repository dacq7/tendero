"""Siembra el primer usuario admin. Idempotente: no duplica si ya existe.

Uso:  python -m app.seed [email] [password] [nombre]
"""

import sys

from sqlmodel import Session

from app.core.security import hash_password
from app.db.session import engine
from app.models.user import UserRole
from app.repositories import user_repository


def seed_admin(email: str, password: str, full_name: str) -> None:
    with Session(engine) as session:
        existing = user_repository.get_by_email(session, email)
        if existing is not None:
            print(f"Admin ya existe: {email} (id={existing.id}) — sin cambios.")
            return
        user = user_repository.create(
            session,
            email=email,
            full_name=full_name,
            hashed_password=hash_password(password),
            role=UserRole.admin,
        )
        print(f"Admin creado: {user.email} (id={user.id}, rol={user.role.value})")


if __name__ == "__main__":
    email = sys.argv[1] if len(sys.argv) > 1 else "admin@tendero.co"
    password = sys.argv[2] if len(sys.argv) > 2 else "Admin1234!"
    full_name = sys.argv[3] if len(sys.argv) > 3 else "Administrador"
    seed_admin(email, password, full_name)
