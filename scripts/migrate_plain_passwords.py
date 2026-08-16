"""Convierte contraseñas en texto plano (pgAdmin) a bcrypt."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import reflex as rx
from sqlmodel import select

from polleria.database import ensure_schema, migrate_plain_passwords, migrate_schema
from polleria.models import User


def is_bcrypt_hash(value: str) -> bool:
    return User.is_bcrypt_hash(value)


def main() -> None:
    ensure_schema()
    migrate_schema()
    n = migrate_plain_passwords()
    with rx.session() as db:
        for user in db.exec(select(User)).all():
            kind = "bcrypt" if is_bcrypt_hash(user.password_hash) else "texto plano"
            print(f"{user.email}: {kind}")
    print(f"Migrados: {n}")


if __name__ == "__main__":
    main()
