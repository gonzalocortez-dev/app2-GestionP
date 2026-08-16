"""Inicialización de esquema. Los modelos deben importarse para registrarse."""

from __future__ import annotations

import reflex as rx
from sqlalchemy import inspect, text
from sqlmodel import SQLModel

from polleria import models as _models  # noqa: F401
from polleria.models import User


def ensure_schema() -> None:
    with rx.session() as session:
        SQLModel.metadata.create_all(session.get_bind())


def migrate_schema() -> None:
    with rx.session() as session:
        bind = session.get_bind()
        insp = inspect(bind)
        if "users" not in insp.get_table_names():
            return
        cols = {c["name"] for c in insp.get_columns("users")}
        if "email_verified" not in cols:
            if bind.dialect.name == "postgresql":
                session.execute(
                    text(
                        "ALTER TABLE users ADD COLUMN email_verified "
                        "BOOLEAN NOT NULL DEFAULT FALSE"
                    )
                )
            else:
                session.execute(
                    text(
                        "ALTER TABLE users ADD COLUMN email_verified "
                        "BOOLEAN NOT NULL DEFAULT 0"
                    )
                )
            session.execute(text("UPDATE users SET email_verified = TRUE"))
            session.commit()


def migrate_plain_passwords() -> int:
    """Hashea contraseñas guardadas en texto plano desde pgAdmin."""
    from sqlmodel import select

    changed = 0
    with rx.session() as session:
        for user in session.exec(select(User)).all():
            if user.password_hash and user.needs_password_hash():
                plain = user.password_hash
                user.password_hash = User.hash_password(plain)
                user.email_verified = True
                session.add(user)
                changed += 1
        if changed:
            session.commit()
    return changed


is_bcrypt_hash = User.is_bcrypt_hash
