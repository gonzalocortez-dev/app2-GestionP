"""Elimina usuarios y datos demo de la base (uso único antes de producción)."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

DEMO_EMAILS = (
    "admin@polleria.com",
    "vendedor@polleria.com",
    "supervisor@polleria.com",
)

TABLES = (
    "auth_sessions",
    "sale_items",
    "sales",
    "expenses",
    "inventory_movements",
    "purchase_items",
    "purchases",
    "cash_register_closures",
    "audit_logs",
    "products",
)


def main() -> None:
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        raise SystemExit("DATABASE_URL no configurada")
    engine = create_engine(url)
    with engine.begin() as conn:
        for table in TABLES:
            conn.execute(text(f"DELETE FROM {table}"))
        for email in DEMO_EMAILS:
            conn.execute(
                text("DELETE FROM users WHERE email = :email"),
                {"email": email},
            )
        remaining = conn.execute(text("SELECT COUNT(*) FROM users")).scalar()
        print(f"Usuarios restantes: {remaining}")
        print("Datos demo eliminados.")


if __name__ == "__main__":
    main()
