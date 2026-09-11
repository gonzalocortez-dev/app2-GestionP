"""Inicialización de esquema. Los modelos deben importarse para registrarse."""

from __future__ import annotations

import reflex as rx
from sqlalchemy import inspect, text
from sqlmodel import SQLModel

from polleria import models as _models  # noqa: F401
from polleria.models import User

_initialized = False


def init_db() -> None:
    """Crea/migra el esquema una sola vez por proceso. No hacerlo en cada página."""
    global _initialized
    if _initialized:
        return
    ensure_schema()
    migrate_schema()
    migrate_plain_passwords()
    _initialized = True


def ensure_schema() -> None:
    with rx.session() as session:
        bind = session.get_bind()
        from polleria.db_url import SQLITE_FORBIDDEN, is_production

        if is_production() and bind.dialect.name == "sqlite":
            raise RuntimeError(SQLITE_FORBIDDEN)
        SQLModel.metadata.create_all(bind)


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
        if "sales" in insp.get_table_names():
            sale_cols = {c["name"] for c in insp.get_columns("sales")}
            if "sucursal" not in sale_cols:
                session.execute(
                    text(
                        "ALTER TABLE sales ADD COLUMN sucursal "
                        "VARCHAR NOT NULL DEFAULT ''"
                    )
                )
                session.commit()
        if "expenses" in insp.get_table_names():
            expense_cols = {c["name"] for c in insp.get_columns("expenses")}
            if "sucursal" not in expense_cols:
                session.execute(
                    text(
                        "ALTER TABLE expenses ADD COLUMN sucursal "
                        "VARCHAR NOT NULL DEFAULT ''"
                    )
                )
                session.commit()
        if "inventory_movements" in insp.get_table_names():
            move_cols = {c["name"] for c in insp.get_columns("inventory_movements")}
            if "sucursal" not in move_cols:
                session.execute(
                    text(
                        "ALTER TABLE inventory_movements ADD COLUMN sucursal "
                        "VARCHAR NOT NULL DEFAULT ''"
                    )
                )
                session.commit()
        if "purchases" in insp.get_table_names():
            purchase_cols = {c["name"] for c in insp.get_columns("purchases")}
            if "sucursal" not in purchase_cols:
                session.execute(
                    text(
                        "ALTER TABLE purchases ADD COLUMN sucursal "
                        "VARCHAR NOT NULL DEFAULT ''"
                    )
                )
                session.commit()
        if "cash_register_closures" in insp.get_table_names():
            cash_cols = {c["name"] for c in insp.get_columns("cash_register_closures")}
            cash_type = (
                "DOUBLE PRECISION"
                if bind.dialect.name == "postgresql"
                else "FLOAT"
            )
            if "total_gastos" not in cash_cols:
                session.execute(
                    text(
                        "ALTER TABLE cash_register_closures ADD COLUMN "
                        f"total_gastos {cash_type} NOT NULL DEFAULT 0"
                    )
                )
            if "ganancia_neta" not in cash_cols:
                session.execute(
                    text(
                        "ALTER TABLE cash_register_closures ADD COLUMN "
                        f"ganancia_neta {cash_type} NOT NULL DEFAULT 0"
                    )
                )
            if "total_gastos" not in cash_cols or "ganancia_neta" not in cash_cols:
                session.commit()
        from polleria.services.stock import seed_legacy_branch_stocks

        seed_legacy_branch_stocks(session)
        if bind.dialect.name == "postgresql":
            _harden_public_access(session)


def _harden_public_access(session) -> None:
    """Activa RLS y cierra PostgREST (anon/authenticated). El rol postgres de la app bypasea RLS."""
    session.execute(
        text(
            """
            DO $$
            DECLARE r record;
            BEGIN
              FOR r IN
                SELECT tablename
                FROM pg_tables
                WHERE schemaname = 'public'
              LOOP
                EXECUTE format(
                  'ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY',
                  r.tablename
                );
                EXECUTE format(
                  'REVOKE ALL ON TABLE public.%I FROM anon, authenticated',
                  r.tablename
                );
              END LOOP;
            END $$
            """
        )
    )
    session.execute(
        text("REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon, authenticated")
    )
    session.execute(
        text(
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
            "REVOKE ALL ON TABLES FROM anon, authenticated"
        )
    )
    session.execute(
        text(
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
            "REVOKE ALL ON SEQUENCES FROM anon, authenticated"
        )
    )
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
