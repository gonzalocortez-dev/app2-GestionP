"""Crea o restablece la cuenta administrador inicial (sin depender de Gmail)."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlmodel import select

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

import reflex as rx

from polleria.database import ensure_schema, migrate_schema
from polleria.models import User

DEFAULT_EMAIL = os.getenv("ADMIN_EMAIL", "admin.lafabrica@gmail.com").strip().lower()
DEFAULT_PASSWORD = os.getenv("ADMIN_PASSWORD", "Polleria123!")


def main() -> None:
    ensure_schema()
    migrate_schema()
    with rx.session() as db:
        user = db.exec(select(User).where(User.email == DEFAULT_EMAIL)).first()
        if user is None:
            user = User(
                nombre="Administrador",
                apellido="Sistema",
                email=DEFAULT_EMAIL,
                password_hash=User.hash_password(DEFAULT_PASSWORD),
                role="admin",
                activo=True,
                email_verified=True,
            )
            db.add(user)
        else:
            user.role = "admin"
            user.activo = True
            user.email_verified = True
            user.password_hash = User.hash_password(DEFAULT_PASSWORD)
            db.add(user)
        db.commit()
    print(f"Admin: {DEFAULT_EMAIL} / {DEFAULT_PASSWORD}")


if __name__ == "__main__":
    main()
