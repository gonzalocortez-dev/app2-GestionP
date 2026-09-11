"""Crea en Supabase las tablas definidas en polleria.models.

Uso (desde la raíz del proyecto):

    .\\.venv\\Scripts\\python.exe scripts\\create_supabase_tables.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlmodel import SQLModel

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from polleria import models as _models  # noqa: F401
from scripts.dburl import explain_connect_error, redact, to_session_pooler


def _load_supabase_url() -> str:
    load_dotenv(ROOT / ".env")
    load_dotenv(ROOT / ".env.supabase", override=True)
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        raise SystemExit("ERROR: DATABASE_URL no está definida en .env.supabase ni .env")
    if "localhost" in url or "127.0.0.1" in url:
        raise SystemExit(
            "ERROR: DATABASE_URL apunta a localhost. "
            "Este script debe usar la URL de Supabase (.env.supabase)."
        )
    if "supabase.co" not in url and "pooler.supabase.com" not in url:
        raise SystemExit(
            "ERROR: DATABASE_URL no parece de Supabase. Abortando para no tocar otra base."
        )
    return to_session_pooler(url)


def main() -> None:
    url = _load_supabase_url()
    print("Destino:", redact(url))
    engine = create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 15})
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        raise SystemExit(explain_connect_error(exc)) from exc
    SQLModel.metadata.create_all(engine)
    tables = sorted(inspect(engine).get_table_names())
    print(f"OK: {len(tables)} tablas en public")
    for name in tables:
        print(f"  - {name}")


if __name__ == "__main__":
    main()
