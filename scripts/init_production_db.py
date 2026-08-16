"""Crea tablas en PostgreSQL de producción (primera vez)."""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

import reflex as rx  # noqa: E402

from polleria.database import ensure_schema, migrate_schema  # noqa: E402


def main() -> None:
    ensure_schema()
    migrate_schema()
    print("OK: esquema creado / migrado en la base de producción.")


if __name__ == "__main__":
    main()
