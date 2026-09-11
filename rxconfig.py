"""Configuración de Reflex. Las credenciales salen de variables de entorno."""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
import reflex as rx

from polleria.db_url import resolve_database_url

load_dotenv(Path(__file__).resolve().parent / ".env")

config = rx.Config(
    app_name="polleria",
    db_url=resolve_database_url(),
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
