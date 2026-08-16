"""Envío de correos vía Gmail SMTP."""

from __future__ import annotations

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from polleria.constants import APP_NAME

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


def is_mail_configured() -> bool:
    user = os.getenv("GMAIL_USER", "").strip()
    password = os.getenv("GMAIL_APP_PASSWORD", "").strip()
    return bool(user and password)


def app_base_url() -> str:
    return os.getenv("APP_BASE_URL", "http://localhost:3000").rstrip("/")


def _from_address() -> str:
    name = os.getenv("MAIL_FROM_NAME", APP_NAME).strip() or APP_NAME
    user = os.getenv("GMAIL_USER", "").strip()
    return f"{name} <{user}>"


def send_email(*, to: str, subject: str, html_body: str, text_body: str) -> None:
    if not is_mail_configured():
        raise RuntimeError(
            "Gmail no configurado. Definí GMAIL_USER y GMAIL_APP_PASSWORD en .env"
        )
    user = os.getenv("GMAIL_USER", "").strip()
    password = os.getenv("GMAIL_APP_PASSWORD", "").replace(" ", "")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = _from_address()
    msg["To"] = to
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(user, password)
        server.sendmail(user, [to], msg.as_string())


def send_verification_email(*, to: str, nombre: str, token: str) -> None:
    link = f"{app_base_url()}/verificar-email/{token}"
    subject = f"Verificá tu email — {APP_NAME}"
    text_body = (
        f"Hola {nombre},\n\n"
        f"Gracias por registrarte en {APP_NAME}.\n"
        f"Verificá tu email con este enlace (válido 24 horas):\n{link}\n\n"
        f"Si no creaste esta cuenta, ignorá este mensaje."
    )
    html_body = f"""
    <div style="font-family:sans-serif;max-width:520px;margin:0 auto">
      <h2>{APP_NAME}</h2>
      <p>Hola <strong>{nombre}</strong>,</p>
      <p>Gracias por registrarte. Verificá tu email para acceder al sistema:</p>
      <p><a href="{link}" style="display:inline-block;padding:12px 20px;background:#ea580c;color:#fff;text-decoration:none;border-radius:8px">Verificar email</a></p>
      <p style="color:#64748b;font-size:14px">El enlace vence en 24 horas.</p>
      <p style="color:#64748b;font-size:14px">Si no creaste esta cuenta, ignorá este mensaje.</p>
    </div>
    """
    send_email(to=to, subject=subject, html_body=html_body, text_body=text_body)


def send_password_reset_email(*, to: str, nombre: str, token: str) -> None:
    link = f"{app_base_url()}/restablecer-contrasena/{token}"
    subject = f"Restablecer contraseña — {APP_NAME}"
    text_body = (
        f"Hola {nombre},\n\n"
        f"Recibimos una solicitud para restablecer tu contraseña.\n"
        f"Usá este enlace (válido 1 hora):\n{link}\n\n"
        f"Si no pediste esto, ignorá el mensaje."
    )
    html_body = f"""
    <div style="font-family:sans-serif;max-width:520px;margin:0 auto">
      <h2>{APP_NAME}</h2>
      <p>Hola <strong>{nombre}</strong>,</p>
      <p>Recibimos una solicitud para restablecer tu contraseña:</p>
      <p><a href="{link}" style="display:inline-block;padding:12px 20px;background:#ea580c;color:#fff;text-decoration:none;border-radius:8px">Restablecer contraseña</a></p>
      <p style="color:#64748b;font-size:14px">El enlace vence en 1 hora.</p>
      <p style="color:#64748b;font-size:14px">Si no pediste esto, ignorá el mensaje.</p>
    </div>
    """
    send_email(to=to, subject=subject, html_body=html_body, text_body=text_body)
