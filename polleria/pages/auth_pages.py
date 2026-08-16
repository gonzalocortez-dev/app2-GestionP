"""Login y registro."""

from __future__ import annotations

import reflex as rx

from polleria.auth.state import AuthState
from polleria.constants import APP_NAME, APP_TAGLINE, LOGO_PATH


def _auth_card(*children) -> rx.Component:
    return rx.center(
        rx.card(
            rx.vstack(
                rx.center(
                    rx.image(
                        src=LOGO_PATH,
                        alt=APP_NAME,
                        width="100%",
                        max_width="320px",
                        height="auto",
                    ),
                    width="100%",
                ),
                rx.vstack(
                    rx.heading(APP_NAME, size="7", text_align="center"),
                    rx.text(
                        APP_TAGLINE,
                        color=rx.color("slate", 11),
                        text_align="center",
                    ),
                    spacing="1",
                    width="100%",
                    align="center",
                ),
                *children,
                spacing="5",
                width="100%",
            ),
            size="4",
            width="100%",
            max_width="440px",
        ),
        min_height="100vh",
        padding="1.25rem",
        background=rx.color("slate", 2),
    )


def login_page() -> rx.Component:
    return _auth_card(
        rx.cond(
            AuthState.db_error != "",
            rx.callout(AuthState.db_error, icon="database", color="red"),
            rx.fragment(),
        ),
        rx.form(
            rx.vstack(
                rx.cond(
                    AuthState.auth_error != "",
                    rx.callout(AuthState.auth_error, icon="triangle-alert", color="red"),
                    rx.fragment(),
                ),
                rx.text("Email", size="2", weight="medium"),
                rx.input(
                    placeholder="tu@email.com",
                    name="email",
                    type="email",
                    size="3",
                    width="100%",
                ),
                rx.text("Contraseña", size="2", weight="medium"),
                rx.input(
                    placeholder="••••••••",
                    name="password",
                    type="password",
                    size="3",
                    width="100%",
                ),
                rx.button(
                    "Ingresar",
                    type="submit",
                    size="3",
                    width="100%",
                    height="48px",
                ),
                spacing="3",
                width="100%",
                align="start",
            ),
            on_submit=AuthState.login,
            reset_on_submit=False,
            width="100%",
        ),
        rx.hstack(
            rx.link("Olvidé mi contraseña", href="/olvide-contrasena", size="2"),
            rx.spacer(),
            rx.text("¿No tenés cuenta?", size="2"),
            rx.link("Registrate", href="/registro", weight="bold"),
            spacing="2",
            width="100%",
            align="center",
        ),
        rx.cond(
            AuthState.pending_email != "",
            rx.form(
                rx.vstack(
                    rx.callout(
                        "¿No recibiste el email de verificación?",
                        icon="mail",
                        color="orange",
                        size="1",
                    ),
                    rx.input(
                        name="email",
                        type="email",
                        default_value=AuthState.pending_email,
                        size="3",
                        width="100%",
                    ),
                    rx.button(
                        "Reenviar verificación",
                        type="submit",
                        variant="soft",
                        width="100%",
                    ),
                    spacing="2",
                    width="100%",
                ),
                on_submit=AuthState.resend_verification,
                reset_on_submit=False,
                width="100%",
            ),
            rx.fragment(),
        ),
        rx.cond(
            AuthState.auth_info != "",
            rx.callout(AuthState.auth_info, icon="info", color="green"),
            rx.fragment(),
        ),
    )


def register_page() -> rx.Component:
    return _auth_card(
        rx.heading("Crear cuenta", size="5"),
        rx.cond(
            AuthState.registration_open,
            rx.callout(
                "Serás administrador porque sos el primer usuario del sistema.",
                icon="shield",
                color="orange",
                size="1",
            ),
            rx.callout(
                "Los nuevos usuarios se registran como vendedores. "
                "El administrador puede cambiar roles después.",
                icon="info",
                color="blue",
                size="1",
            ),
        ),
        rx.form(
            rx.vstack(
                rx.cond(
                    AuthState.auth_error != "",
                    rx.callout(AuthState.auth_error, icon="triangle-alert", color="red"),
                    rx.fragment(),
                ),
                rx.input(
                    placeholder="Nombre",
                    name="nombre",
                    size="3",
                    width="100%",
                ),
                rx.input(
                    placeholder="Apellido",
                    name="apellido",
                    size="3",
                    width="100%",
                ),
                rx.input(
                    placeholder="Email",
                    name="email",
                    type="email",
                    size="3",
                    width="100%",
                ),
                rx.input(
                    placeholder="Contraseña (mín. 8)",
                    name="password",
                    type="password",
                    size="3",
                    width="100%",
                ),
                rx.input(
                    placeholder="Repetir contraseña",
                    name="password2",
                    type="password",
                    size="3",
                    width="100%",
                ),
                rx.button(
                    "Crear cuenta",
                    type="submit",
                    size="3",
                    width="100%",
                    height="48px",
                ),
                spacing="3",
                width="100%",
            ),
            on_submit=AuthState.register,
            reset_on_submit=False,
            width="100%",
        ),
        rx.link("Ya tengo cuenta", href="/login"),
    )


def forgot_password_page() -> rx.Component:
    return _auth_card(
        rx.heading("Recuperar contraseña", size="5"),
        rx.text(
            "Te enviaremos un enlace a tu email registrado.",
            size="2",
            color=rx.color("slate", 11),
        ),
        rx.cond(
            AuthState.forgot_sent,
            rx.callout(AuthState.auth_info, icon="mail", color="green"),
            rx.form(
                rx.vstack(
                    rx.cond(
                        AuthState.auth_error != "",
                        rx.callout(
                            AuthState.auth_error,
                            icon="triangle-alert",
                            color="red",
                        ),
                        rx.fragment(),
                    ),
                    rx.input(
                        placeholder="tu@email.com",
                        name="email",
                        type="email",
                        size="3",
                        width="100%",
                    ),
                    rx.button(
                        "Enviar enlace",
                        type="submit",
                        size="3",
                        width="100%",
                    ),
                    spacing="3",
                    width="100%",
                ),
                on_submit=AuthState.forgot_password,
                reset_on_submit=False,
                width="100%",
            ),
        ),
        rx.link("Volver al ingreso", href="/login"),
    )


def reset_password_page() -> rx.Component:
    return _auth_card(
        rx.heading("Nueva contraseña", size="5"),
        rx.cond(
            AuthState.auth_error != "",
            rx.callout(AuthState.auth_error, icon="triangle-alert", color="red"),
            rx.fragment(),
        ),
        rx.cond(
            AuthState.auth_error == "",
            rx.form(
                rx.vstack(
                    rx.input(
                        placeholder="Nueva contraseña (mín. 8)",
                        name="password",
                        type="password",
                        size="3",
                        width="100%",
                    ),
                    rx.input(
                        placeholder="Repetir contraseña",
                        name="password2",
                        type="password",
                        size="3",
                        width="100%",
                    ),
                    rx.button(
                        "Guardar contraseña",
                        type="submit",
                        size="3",
                        width="100%",
                    ),
                    spacing="3",
                    width="100%",
                ),
                on_submit=AuthState.reset_password,
                reset_on_submit=False,
                width="100%",
            ),
            rx.link("Solicitar nuevo enlace", href="/olvide-contrasena"),
        ),
        rx.link("Volver al ingreso", href="/login"),
    )


def verify_pending_page() -> rx.Component:
    return _auth_card(
        rx.heading("Verificá tu email", size="5"),
        rx.callout(
            "Te enviamos un enlace de verificación. Revisá inbox y spam.",
            icon="mail",
            color="orange",
            size="2",
        ),
        rx.form(
            rx.vstack(
                rx.cond(
                    AuthState.auth_error != "",
                    rx.callout(AuthState.auth_error, icon="triangle-alert", color="red"),
                    rx.fragment(),
                ),
                rx.cond(
                    AuthState.auth_info != "",
                    rx.callout(AuthState.auth_info, icon="info", color="green"),
                    rx.fragment(),
                ),
                rx.input(
                    placeholder="Email",
                    name="email",
                    type="email",
                    default_value=AuthState.pending_email,
                    size="3",
                    width="100%",
                ),
                rx.button(
                    "Reenviar email",
                    type="submit",
                    variant="soft",
                    width="100%",
                ),
                spacing="3",
                width="100%",
            ),
            on_submit=AuthState.resend_verification,
            reset_on_submit=False,
            width="100%",
        ),
        rx.link("Ya verifiqué — Ir a ingresar", href="/login"),
    )


def verify_link_page() -> rx.Component:
    return _auth_card(
        rx.center(rx.spinner(size="3"), padding="2rem"),
        rx.text("Verificando email...", size="3"),
    )
