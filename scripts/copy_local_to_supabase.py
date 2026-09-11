"""Copia filas de PostgreSQL local (app_gestionP) a Supabase.

Respeta el orden de claves foráneas vía SQLModel.metadata.sorted_tables.
Preserva IDs y luego ajusta las secuencias SERIAL/IDENTITY.

Uso (desde la raíz del proyecto):

    .\\.venv\\Scripts\\python.exe scripts\\copy_local_to_supabase.py
    .\\.venv\\Scripts\\python.exe scripts\\copy_local_to_supabase.py --dry-run
    .\\.venv\\Scripts\\python.exe scripts\\copy_local_to_supabase.py --force
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlmodel import SQLModel

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from polleria import models as _models  # noqa: F401
from scripts.dburl import explain_connect_error, redact, to_session_pooler


def _load_url(path: Path, *, require_local: bool = False, require_supabase: bool = False) -> str:
    if not path.exists():
        raise SystemExit(f"ERROR: no existe {path}")
    url = ""
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("DATABASE_URL="):
            url = stripped.split("=", 1)[1].strip().strip('"').strip("'")
            break
    if not url:
        raise SystemExit(f"ERROR: no hay DATABASE_URL en {path.name}")
    host = (urlparse(url).hostname or "").lower()
    if require_local and host not in {"localhost", "127.0.0.1"}:
        raise SystemExit(f"ERROR: el origen debe ser localhost, no {host}")
    if require_supabase:
        if "supabase" not in host:
            raise SystemExit(f"ERROR: el destino debe ser Supabase, no {host}")
        url = to_session_pooler(url)
    return url


def _row_dicts(engine: Engine, table) -> list[dict]:
    with engine.connect() as conn:
        result = conn.execute(table.select().order_by(*list(table.primary_key.columns)))
        return [dict(row) for row in result.mappings().all()]


def _count(engine: Engine, table_name: str) -> int:
    with engine.connect() as conn:
        return int(conn.execute(text(f'SELECT COUNT(*) FROM "{table_name}"')).scalar() or 0)


def _reset_id_sequence(conn, table_name: str) -> None:
    seq = conn.execute(
        text("SELECT pg_get_serial_sequence(:tbl, 'id')"),
        {"tbl": table_name},
    ).scalar()
    if not seq:
        return
    conn.execute(
        text(
            "SELECT setval(:seq, COALESCE((SELECT MAX(id) FROM "
            f'"{table_name}"), 1), true)'
        ),
        {"seq": seq},
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Copia app_gestionP local -> Supabase")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Solo muestra conteos; no escribe en Supabase",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Copia aunque el destino ya tenga filas (puede fallar por unique/PK)",
    )
    args = parser.parse_args()

    source_url = _load_url(ROOT / ".env.local", require_local=True)
    target_url = _load_url(ROOT / ".env.supabase", require_supabase=True)

    print("Origen :", redact(source_url))
    print("Destino:", redact(target_url))

    source = create_engine(source_url, pool_pre_ping=True)
    target = create_engine(
        target_url, pool_pre_ping=True, connect_args={"connect_timeout": 15}
    )

    tables = [t for t in SQLModel.metadata.sorted_tables if t.name != "alembic_version"]
    print(f"Tablas ({len(tables)}), orden FK:")
    for table in tables:
        print(f"  {table.name}")

    try:
        target_names = set(inspect(target).get_table_names())
    except Exception as exc:
        raise SystemExit(explain_connect_error(exc)) from exc
    missing = [t.name for t in tables if t.name not in target_names]
    if missing:
        raise SystemExit(
            "ERROR: faltan tablas en Supabase: "
            + ", ".join(missing)
            + ". Ejecutá antes: python scripts/create_supabase_tables.py"
        )

    occupied = []
    if not args.force:
        for table in tables:
            n = _count(target, table.name)
            if n:
                occupied.append(f"{table.name}={n}")
        if occupied:
            raise SystemExit(
                "ERROR: Supabase ya tiene datos ("
                + ", ".join(occupied)
                + "). Usá --force solo si sabés lo que hacés."
            )

    payloads: list[tuple[object, list[dict]]] = []
    for table in tables:
        rows = _row_dicts(source, table)
        payloads.append((table, rows))
        print(f"  {table.name}: {len(rows)} filas en origen")

    if args.dry_run:
        print("Dry-run: no se escribió nada.")
        return

    with target.begin() as conn:
        for table, rows in payloads:
            if not rows:
                continue
            conn.execute(table.insert(), rows)
            print(f"  copiadas {len(rows)} -> {table.name}")
        for table, _rows in payloads:
            if "id" in table.columns:
                _reset_id_sequence(conn, table.name)

    print("Verificación destino:")
    for table in tables:
        print(f"  {table.name}: {_count(target, table.name)}")
    print("OK: copia local -> Supabase terminada.")


if __name__ == "__main__":
    main()
