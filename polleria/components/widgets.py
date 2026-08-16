"""Componentes visuales reutilizables."""

from __future__ import annotations

import reflex as rx


def kpi_card(title: str, value, icon: str, accent: str = "orange", hint: str | None = None) -> rx.Component:
    return rx.card(
        rx.hstack(
            rx.center(
                rx.icon(icon, size=22, color="white"),
                width="44px",
                height="44px",
                border_radius="12px",
                background=rx.color(accent, 9),
                flex_shrink="0",
            ),
            rx.vstack(
                rx.text(title, size="2", color=rx.color("slate", 11), weight="medium"),
                rx.heading(value, size="6", weight="bold"),
                rx.cond(
                    hint is not None,
                    rx.text(hint or "", size="1", color=rx.color("slate", 10)),
                    rx.fragment(),
                ),
                spacing="1",
                align="start",
            ),
            spacing="3",
            align="center",
            width="100%",
        ),
        size="2",
        width="100%",
        style={"box_shadow": "0 1px 2px rgba(15,23,42,0.06)"},
    )


def section_card(*children, **kwargs) -> rx.Component:
    return rx.card(
        rx.vstack(*children, spacing="4", width="100%", align="start"),
        size="2",
        width="100%",
        **kwargs,
    )


def page_header(title: str, subtitle: str = "", extra: rx.Component | None = None) -> rx.Component:
    return rx.hstack(
        rx.vstack(
            rx.heading(title, size="7"),
            rx.cond(
                subtitle != "",
                rx.text(subtitle, color=rx.color("slate", 11), size="3"),
                rx.fragment(),
            ),
            spacing="1",
            align="start",
        ),
        extra or rx.fragment(),
        justify="between",
        align="center",
        width="100%",
        wrap="wrap",
        spacing="3",
    )


def empty_state(text: str, icon: str = "inbox") -> rx.Component:
    return rx.center(
        rx.vstack(
            rx.icon(icon, size=32, color=rx.color("slate", 8)),
            rx.text(text, color=rx.color("slate", 11)),
            align="center",
            spacing="2",
        ),
        padding="2.5rem",
        width="100%",
    )


def status_badge(estado: rx.Var | str) -> rx.Component:
    return rx.match(
        estado,
        ("stock_normal", rx.badge("Stock normal", color_scheme="green", variant="soft")),
        ("stock_bajo", rx.badge("Stock bajo", color_scheme="amber", variant="soft")),
        ("sin_stock", rx.badge("Sin stock", color_scheme="red", variant="soft")),
        rx.badge(estado, variant="soft"),
    )


def table_wrap(*children) -> rx.Component:
    return rx.box(
        *children,
        width="100%",
        overflow_x="auto",
    )


def labeled_input(label: str, **input_props) -> rx.Component:
    return rx.vstack(
        rx.text(label, size="2", weight="medium", color=rx.color("slate", 12)),
        rx.input(size="3", width="100%", **input_props),
        spacing="1",
        width="100%",
        align="start",
    )


def labeled_select(label: str, items, **select_props) -> rx.Component:
    return rx.vstack(
        rx.text(label, size="2", weight="medium", color=rx.color("slate", 12)),
        rx.select(items, size="3", width="100%", **select_props),
        spacing="1",
        width="100%",
        align="start",
    )


def labeled_native_select(label: str, items, **select_props) -> rx.Component:
    """Select HTML nativo (no controlado): funciona en formularios y diálogos."""
    select_props = dict(select_props)
    # default_value reactivo bloquea el cambio de opción en Reflex/React.
    select_props.pop("default_value", None)
    select_props.pop("value", None)
    return rx.vstack(
        rx.text(label, size="2", weight="medium", color=rx.color("slate", 12)),
        rx.el.select(
            rx.foreach(
                items,
                lambda item: rx.el.option(item, value=item),
            ),
            width="100%",
            padding="0.55rem 0.65rem",
            border_radius="8px",
            border=f"1px solid {rx.color('slate', 6)}",
            background="white",
            font_size="15px",
            cursor="pointer",
            **select_props,
        ),
        spacing="1",
        width="100%",
        align="start",
    )
