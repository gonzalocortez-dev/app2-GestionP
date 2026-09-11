"""Resolución de DATABASE_URL. En Cloud nunca se usa SQLite."""

from __future__ import annotations

import os
from urllib.parse import quote, unquote, urlparse, urlunparse

PROJECT_REF = "bzhhjezqmwstgtfvrzxx"
POOLER_HOST = "aws-0-us-east-2.pooler.supabase.com"
SESSION_PORT = 5432

SQLITE_FORBIDDEN = (
    "Esta app no puede usar SQLite en producción: los datos se pierden "
    "al reiniciar Reflex Cloud. Configurá el Secret DATABASE_URL con "
    "Supabase Session pooler (IPv4)."
)


def is_production() -> bool:
    if os.getenv("REFLEX_IS_REFLEX_CLOUD", "").strip().lower() in {"1", "true", "yes"}:
        return True
    return os.getenv("APP_ENV", "").strip().lower() in {"production", "prod"}


def redact(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.hostname or "?"
    port = parsed.port or ""
    db = (parsed.path or "/").lstrip("/") or "?"
    return f"{parsed.scheme}://{parsed.username}:[REDACTED]@{host}:{port}/{db}"


def to_psycopg(url: str) -> str:
    url = url.strip()
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


def ensure_ssl(url: str) -> str:
    if "sslmode=" in url:
        return url
    return url + ("&" if "?" in url else "?") + "sslmode=require"


def to_session_pooler(url: str) -> str:
    """db.PROJECT.supabase.co (IPv6) → Session pooler IPv4 en us-east-2."""
    url = ensure_ssl(to_psycopg(url))
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if "pooler.supabase.com" in host:
        return url
    if host != f"db.{PROJECT_REF}.supabase.co":
        return url

    password = unquote(parsed.password or "")
    user = f"postgres.{PROJECT_REF}"
    netloc = f"{user}:{quote(password, safe='')}@{POOLER_HOST}:{SESSION_PORT}"
    rewritten = urlunparse(parsed._replace(netloc=netloc))
    return ensure_ssl(rewritten)


def explain_connect_error(exc: BaseException) -> str:
    text = str(exc)
    if "getaddrinfo failed" in text or "could not translate host name" in text:
        return (
            "No se pudo resolver db.*.supabase.co (ese host es IPv6).\n"
            "Usá Session pooler (IPv4):\n"
            f"  HOST: {POOLER_HOST}\n"
            f"  PORT: {SESSION_PORT}\n"
            f"  USER: postgres.{PROJECT_REF}\n"
            "Copiá la URI en Supabase → Connect → Session pooler."
        )
    if "password authentication failed" in text:
        return (
            "Supabase rechazó la contraseña. "
            "Project Settings → Database → Reset database password, "
            "después actualizá DATABASE_URL (Session pooler) en .env.supabase "
            "y en Reflex Cloud → Settings → Secrets."
        )
    if "tenant/user" in text:
        return (
            "El pooler no reconoce este proyecto en esa región. "
            "Copiá la URI exacta de Connect → Session pooler."
        )
    return text[:500]


def resolve_database_url() -> str:
    raw = os.getenv("DATABASE_URL", "").strip()
    production = is_production()

    if production:
        if not raw or raw.startswith("sqlite"):
            raise RuntimeError(SQLITE_FORBIDDEN)
        if "localhost" in raw or "127.0.0.1" in raw:
            raise RuntimeError(
                "DATABASE_URL apunta a localhost. Reflex Cloud no puede usar "
                "PostgreSQL de tu PC. Usá Supabase Session pooler."
            )
        url = to_session_pooler(raw)
        print(f"DB producción: {redact(url)}", flush=True)
        return url

    if not raw:
        print("DB desarrollo: sqlite:///polleria.db (no usar en Cloud)", flush=True)
        return "sqlite:///polleria.db"

    url = to_session_pooler(raw) if "supabase" in raw else raw
    print(f"DB desarrollo: {redact(url)}", flush=True)
    return url
