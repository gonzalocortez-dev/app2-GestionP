"""Estado de navegación (menú hamburguesa en celular)."""

from __future__ import annotations

import reflex as rx

from polleria.auth.state import AuthState


class NavState(AuthState):
    sidebar_open: bool = False

    @rx.event
    def toggle_sidebar(self):
        self.sidebar_open = not self.sidebar_open

    @rx.event
    def close_sidebar(self):
        self.sidebar_open = False
