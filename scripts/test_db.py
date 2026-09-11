"""Prueba conexión a PostgreSQL (Supabase / producción)."""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from polleria.db_url import explain_connect_error, redact, to_session_pooler

load_dotenv(ROOT / ".env")
load_dotenv(ROOT / ".env.supabase", override=True)

import os

url = os.getenv("DATABASE_URL", "").strip()
if not url:
    print("ERROR: DATABASE_URL no está definida en .env.supabase ni .env")
    sys.exit(1)

if "localhost" in url or "127.0.0.1" in url:
    print("ERROR: DATABASE_URL apunta a localhost. Usá la URL de Supabase.")
    sys.exit(1)

url = to_session_pooler(url)
print("Destino:", redact(url))

try:
    engine = create_engine(
        url, pool_pre_ping=True, connect_args={"connect_timeout": 15}
    )
    with engine.connect() as conn:
        version = conn.execute(text("SELECT version()")).scalar()
    print("OK: conexión exitosa")
    print((version or "")[:80] + "...")
except Exception as exc:
    print(explain_connect_error(exc))
    sys.exit(1)
