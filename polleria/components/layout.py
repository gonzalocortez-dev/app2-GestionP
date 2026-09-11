"""Shell principal: sidebar, header y menú móvil."""

from __future__ import annotations

import reflex as rx

from polleria.auth.state import AuthState
from polleria.constants import APP_TAGLINE, LOGO_PATH
from polleria.states.nav import NavState


def _nav_item(label: str, href: str, icon: str, visible) -> rx.Component:
    active = AuthState.router.url.path == href
    return rx.cond(
        visible,
        rx.link(
            rx.hstack(
                rx.icon(icon, size=18),
                rx.text(label, size="3", weight="medium"),
                spacing="3",
                align="center",
                width="100%",
                padding="0.7rem 0.85rem",
                border_radius="10px",
                color=rx.cond(active, "white", rx.color("slate", 11)),
                background=rx.cond(active, rx.color("orange", 9), "transparent"),
                _hover={
                    "background": rx.cond(active, rx.color("orange", 9), rx.color("slate", 3)),
                },
            ),
            href=href,
            width="100%",
            text_decoration="none",
            on_click=NavState.close_sidebar,
        ),
        rx.fragment(),
    )


def _nav_links() -> rx.Component:
    return rx.vstack(
        _nav_item("Dashboard", "/", "layout-dashboard", AuthState.can_see_dashboard),
        _nav_item("Punto de Venta", "/pos", "shopping-cart", AuthState.can_use_pos),
        _nav_item("Ventas", "/ventas", "receipt", AuthState.can_view_sales),
        _nav_item("Productos", "/productos", "utensils", AuthState.can_view_products),
        _nav_item("Inventario", "/inventario", "warehouse", AuthState.can_view_inventory),
        _nav_item("Gastos", "/gastos", "wallet", AuthState.can_manage_expenses),
        _nav_item("Compras", "/compras", "package-plus", AuthState.can_view_purchases),
        _nav_item("Vendedores", "/vendedores", "users", AuthState.can_view_sellers),
        _nav_item("Cierre de caja", "/caja", "landmark", AuthState.can_close_cash),
        _nav_item("Reportes", "/reportes", "chart-column", AuthState.can_view_reports),
        _nav_item("Usuarios", "/usuarios", "shield", AuthState.can_manage_users),
        _nav_item("Configuración", "/configuracion", "settings", AuthState.can_manage_settings),
        spacing="1",
        width="100%",
        align="start",
    )


def _logout_button(**props) -> rx.Component:
    return rx.button(
        rx.icon("log-out", size=16),
        "Cerrar sesión",
        on_click=AuthState.logout,
        variant="soft",
        color_scheme="gray",
        size="3",
        **props,
    )


def sidebar() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.image(
                    src=LOGO_PATH,
                    alt=AuthState.business_name,
                    width="40px",
                    height="40px",
                    border_radius="10px",
                    object_fit="cover",
                ),
                rx.vstack(
                    rx.text(AuthState.business_name, weight="bold", size="4"),
                    rx.text(APP_TAGLINE, size="1", color=rx.color("slate", 10)),
                    spacing="0",
                    align="start",
                ),
                spacing="3",
                padding="0.4rem 0.4rem 1rem 0.4rem",
                width="100%",
            ),
            _nav_links(),
            rx.spacer(),
            rx.hstack(
                rx.avatar(fallback=AuthState.authenticated_user.nombre[:1], size="2"),
                rx.vstack(
                    rx.text(AuthState.authenticated_user.nombre_completo, size="2", weight="medium"),
                    rx.badge(AuthState.role, color_scheme="orange", variant="soft"),
                    spacing="0",
                    align="start",
                ),
                spacing="2",
                width="100%",
            ),
            _logout_button(width="100%"),
            spacing="3",
            height="100%",
            width="100%",
        ),
        width="260px",
        min_width="260px",
        height="100vh",
        padding="1rem",
        background="white",
        border_right=f"1px solid {rx.color('slate', 4)}",
        position="sticky",
        top="0",
        display=["none", "none", "flex"],
    )


def mobile_header(title: str) -> rx.Component:
    return rx.hstack(
        rx.drawer.root(
            rx.drawer.trigger(
                rx.icon_button(
                    rx.icon("menu", size=20),
                    variant="soft",
                    color_scheme="gray",
                    size="3",
                ),
            ),
            rx.drawer.overlay(z_index="20"),
            rx.drawer.portal(
                rx.drawer.content(
                    rx.vstack(
                        rx.hstack(
                            rx.heading("Menú", size="5"),
                            rx.drawer.close(
                                rx.icon_button(rx.icon("x"), variant="ghost", color_scheme="gray"),
                            ),
                            justify="between",
                            width="100%",
                        ),
                        _nav_links(),
                        _logout_button(width="100%"),
                        spacing="4",
                        width="100%",
                    ),
                    top="0",
                    left="0",
                    right="auto",
                    height="100%",
                    width="280px",
                    padding="1.25rem",
                    background="white",
                )
            ),
            direction="left",
        ),
        rx.heading(title, size="5"),
        rx.spacer(),
        rx.badge(AuthState.authenticated_user.nombre, variant="soft", color_scheme="orange"),
        _logout_button(),
        width="100%",
        padding="0.85rem 1rem",
        background="white",
        border_bottom=f"1px solid {rx.color('slate', 4)}",
        position="sticky",
        top="0",
        z_index="10",
        display=["flex", "flex", "none"],
        align="center",
    )


def app_shell(title: str, *children, extra: rx.Component | None = None) -> rx.Component:
    return rx.hstack(
        sidebar(),
        rx.box(
            mobile_header(title),
            rx.box(
                rx.vstack(
                    rx.hstack(
                        rx.heading(title, size="7"),
                        rx.hstack(
                            extra or rx.fragment(),
                            _logout_button(),
                            spacing="3",
                            align="center",
                        ),
                        justify="between",
                        align="center",
                        width="100%",
                        wrap="wrap",
                        display=["none", "none", "flex"],
                    ),
                    *children,
                    spacing="4",
                    width="100%",
                    align="start",
                ),
                padding=["1rem", "1.1rem", "1.5rem"],
                width="100%",
                max_width="1400px",
                margin="0 auto",
            ),
            width="100%",
            min_height="100vh",
            background=rx.color("slate", 2),
        ),
        spacing="0",
        align="start",
        width="100%",
        min_height="100vh",
    )


def unauthorized() -> rx.Component:
    return app_shell(
        "Sin acceso",
        rx.callout(
            "Tu rol no permite ver esta sección.",
            icon="shield-alert",
            color="red",
        ),
    )
