"""Prueba conexión a PostgreSQL (Supabase / producción)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

url = os.getenv("DATABASE_URL", "").strip()
if not url:
    print("ERROR: DATABASE_URL no está definida en .env")
    sys.exit(1)

if "localhost" in url or "127.0.0.1" in url:
    print("ERROR: DATABASE_URL apunta a localhost. Usá la URL de Supabase.")
    sys.exit(1)

try:
    from sqlalchemy import create_engine, text

    engine = create_engine(url)
    with engine.connect() as conn:
        version = conn.execute(text("SELECT version()")).scalar()
    print("OK: conexión exitosa")
    print(version[:80] + "...")
except Exception as exc:
    print(f"ERROR: no se pudo conectar — {exc}")
    sys.exit(1)
