"""Configuración de Reflex. Las credenciales salen de variables de entorno."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
import reflex as rx

load_dotenv(Path(__file__).resolve().parent / ".env")

_db_url = os.getenv("DATABASE_URL", "").strip()
if not _db_url:
    # Desarrollo local sin PostgreSQL. En producción (Reflex Cloud) definir DATABASE_URL.
    _db_url = "sqlite:///polleria.db"

config = rx.Config(
    app_name="polleria",
    db_url=_db_url,
    telemetry_enabled=False,
    state_auto_setters=True,
    plugins=[
        rx.plugins.SitemapPlugin,
        rx.plugins.RadixThemesPlugin(
            theme=rx.theme(
                appearance="light",
                accent_color="orange",
                gray_color="slate",
                radius="large",
                scaling="110%",
            )
        ),
    ],
)
