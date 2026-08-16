"""Autenticación con hashing bcrypt y sesión persistente."""

from __future__ import annotations

import datetime
from dataclasses import dataclass

import reflex as rx
from sqlmodel import select

from polleria.auth.permissions import has_permission
from polleria.constants import APP_NAME
from polleria.database import ensure_schema, migrate_plain_passwords, migrate_schema
from polleria.models import AuthSession, BusinessSettings, User
from polleria.services.auth_tokens import (
    consume_token,
    issue_password_reset,
    issue_verification,
    validate_reset_token,
    verify_email_token,
)
from polleria.services.email import is_mail_configured
from polleria.services.seed import seed_if_empty
from polleria.utils.time import now_utc

AUTH_TOKEN_KEY = "_polleria_auth"
SESSION_DAYS = 7


@dataclass
class UserInfo:
    id: int = -1
    nombre: str = ""
    apellido: str = ""
    nombre_completo: str = ""
    email: str = ""
    role: str = ""
    activo: bool = False


class AuthState(rx.State):
    auth_token: str = rx.LocalStorage(name=AUTH_TOKEN_KEY)
    auth_error: str = ""
    db_error: str = ""
    business_name: str = APP_NAME
    users_exist: bool = False
    login_email: str = ""
    login_password: str = ""
    reg_nombre: str = ""
    reg_apellido: str = ""
    reg_email: str = ""
    reg_password: str = ""
    reg_password2: str = ""
    pending_email: str = ""
    route_token: str = ""
    auth_info: str = ""
    forgot_sent: bool = False

    @rx.var(cache=True)
    def authenticated_user(self) -> UserInfo:
        dummy = UserInfo()
        token = self.auth_token
        if not token:
            return dummy
        try:
            with rx.session() as session:
                row = session.exec(
                    select(User, AuthSession).where(
                        AuthSession.session_id == token,
                        AuthSession.expiration >= now_utc(),
                        User.id == AuthSession.user_id,
                        User.activo == True,  # noqa: E712
                    )
                ).first()
                if not row:
                    return dummy
                user, _sess = row
                return UserInfo(
                    id=user.id or -1,
                    nombre=user.nombre,
                    apellido=user.apellido,
                    nombre_completo=user.nombre_completo,
                    email=user.email,
                    role=user.role,
                    activo=user.activo,
                )
        except Exception:
            return dummy

    @rx.var(cache=True)
    def is_authenticated(self) -> bool:
        return self.authenticated_user.id >= 0

    @rx.var(cache=True)
    def role(self) -> str:
        return self.authenticated_user.role

    @rx.var(cache=True)
    def is_admin(self) -> bool:
        return self.role == "admin"

    @rx.var(cache=True)
    def is_vendedor(self) -> bool:
        return self.role == "vendedor"

    @rx.var(cache=True)
    def registration_open(self) -> bool:
        return not self.users_exist

    @rx.var(cache=True)
    def can_see_profits(self) -> bool:
        return has_permission(self.role, "profits.view")

    @rx.var(cache=True)
    def can_manage_products(self) -> bool:
        return has_permission(self.role, "products.manage")

    @rx.var(cache=True)
    def can_manage_inventory(self) -> bool:
        return has_permission(self.role, "inventory.manage")

    @rx.var(cache=True)
    def can_manage_expenses(self) -> bool:
        return has_permission(self.role, "expenses.manage")

    @rx.var(cache=True)
    def can_manage_purchases(self) -> bool:
        return has_permission(self.role, "purchases.manage")

    @rx.var(cache=True)
    def can_view_purchases(self) -> bool:
        return has_permission(self.role, "purchases.view")

    @rx.var(cache=True)
    def can_view_inventory(self) -> bool:
        return has_permission(self.role, "inventory.view")

    @rx.var(cache=True)
    def can_view_sellers(self) -> bool:
        return has_permission(self.role, "sellers.view")

    @rx.var(cache=True)
    def can_view_reports(self) -> bool:
        return has_permission(self.role, "reports.view")

    @rx.var(cache=True)
    def can_manage_users(self) -> bool:
        return has_permission(self.role, "users.manage")

    @rx.var(cache=True)
    def can_manage_settings(self) -> bool:
        return has_permission(self.role, "settings.manage")

    @rx.var(cache=True)
    def can_view_all_sales(self) -> bool:
        return has_permission(self.role, "sales.view_all")

    def _has(self, permission: str) -> bool:
        return has_permission(self.authenticated_user.role, permission)

    def _require(self, permission: str) -> None:
        from polleria.services.core import require_perm

        require_perm(self.authenticated_user.role, permission)

    def _bootstrap(self) -> None:
        try:
            ensure_schema()
            migrate_schema()
            migrate_plain_passwords()
            seed_if_empty()
            with rx.session() as session:
                settings = session.exec(select(BusinessSettings)).first()
                if settings:
                    self.business_name = settings.nombre_comercio
                self.users_exist = (
                    session.exec(select(User).limit(1)).first() is not None
                )
            self.db_error = ""
        except Exception:
            self.db_error = (
                "No se pudo conectar a la base de datos. "
                "Verificá DATABASE_URL y que PostgreSQL esté disponible."
            )

    @rx.event
    def bootstrap(self):
        self._bootstrap()

    @rx.event
    def require_login(self):
        self._bootstrap()
        if self.db_error:
            return rx.redirect("/login")
        if not self.is_authenticated:
            return rx.redirect("/login")
        self._touch()

    @rx.event
    def require_guest(self):
        self._bootstrap()
        if self.is_authenticated and not self.db_error:
            return rx.redirect("/")

    @rx.event
    def require_registration(self):
        self._bootstrap()
        if self.is_authenticated and not self.db_error:
            return rx.redirect("/")

    def _touch(self) -> None:
        if self.authenticated_user.id < 0:
            return
        try:
            with rx.session() as session:
                user = session.get(User, self.authenticated_user.id)
                if user:
                    user.last_activity = now_utc()
                    session.add(user)
                    session.commit()
        except Exception:
            pass

    def _login(self, user_id: int) -> None:
        self.do_logout()
        token = self.auth_token or self.router.session.client_token
        self.auth_token = token
        with rx.session() as session:
            session.add(
                AuthSession(
                    user_id=user_id,
                    session_id=token,
                    expiration=now_utc() + datetime.timedelta(days=SESSION_DAYS),
                )
            )
            user = session.get(User, user_id)
            if user:
                user.last_activity = now_utc()
                session.add(user)
            session.commit()

    @rx.event
    def do_logout(self):
        token = self.auth_token
        if token:
            try:
                with rx.session() as session:
                    for row in session.exec(
                        select(AuthSession).where(AuthSession.session_id == token)
                    ).all():
                        session.delete(row)
                    session.commit()
            except Exception:
                pass
        self.auth_token = self.auth_token
        self.auth_error = ""

    @rx.event
    def logout(self):
        self.do_logout()
        self.auth_token = ""
        return rx.redirect("/login")

    @rx.event
    def login(self, form_data: dict):
        self.auth_error = ""
        email = (form_data.get("email") or self.login_email or "").strip().lower()
        password = form_data.get("password") or self.login_password or ""
        if not email or not password:
            self.auth_error = "Ingresá email y contraseña."
            return
        try:
            with rx.session() as session:
                user = session.exec(select(User).where(User.email == email)).first()
                if user is None or not user.verify_password(password):
                    self.auth_error = "Email o contraseña incorrectos."
                    return
                if not user.activo:
                    self.auth_error = "El usuario está desactivado."
                    return
                if is_mail_configured() and not user.email_verified:
                    self.auth_error = (
                        "Verificá tu email antes de ingresar. "
                        "Revisá tu bandeja o solicitá un nuevo enlace abajo."
                    )
                    self.pending_email = user.email
                    return
                if user.needs_password_hash():
                    user.password_hash = User.hash_password(password)
                    user.email_verified = True
                    session.add(user)
                    session.commit()
                self._login(user.id)
        except Exception:
            self.auth_error = (
                "No se pudo conectar a la base de datos. Revisá DATABASE_URL."
            )
            return
        self.login_email = ""
        self.login_password = ""
        return rx.redirect("/")

    @rx.event
    def register(self, form_data: dict):
        self.auth_error = ""
        nombre = (form_data.get("nombre") or self.reg_nombre or "").strip()
        apellido = (form_data.get("apellido") or self.reg_apellido or "").strip()
        email = (form_data.get("email") or self.reg_email or "").strip().lower()
        password = form_data.get("password") or self.reg_password or ""
        password2 = form_data.get("password2") or self.reg_password2 or ""
        if not nombre or not email or not password:
            self.auth_error = "Completá nombre, email y contraseña."
            return
        if "@" not in email or "." not in email:
            self.auth_error = "Ingresá un email válido."
            return
        if len(password) < 8:
            self.auth_error = "La contraseña debe tener al menos 8 caracteres."
            return
        if password != password2:
            self.auth_error = "Las contraseñas no coinciden."
            return
        try:
            with rx.session() as session:
                if session.exec(select(User).where(User.email == email)).first():
                    self.auth_error = "Ya existe un usuario con ese email."
                    return
                existing = session.exec(select(User).limit(1)).first()
                role = "admin" if existing is None else "vendedor"
                user = User(
                    nombre=nombre,
                    apellido=apellido,
                    email=email,
                    password_hash=User.hash_password(password),
                    role=role,
                    activo=True,
                )
                session.add(user)
                session.commit()
                session.refresh(user)
                self.users_exist = True
                try:
                    issue_verification(session, user)
                except Exception:
                    self.auth_error = (
                        "Cuenta creada pero no se pudo enviar el email. "
                        "Configurá Gmail en .env o contactá al administrador."
                    )
                    return
        except Exception:
            self.auth_error = "No se pudo registrar. Revisá la conexión a la base."
            return
        self.reg_nombre = ""
        self.reg_apellido = ""
        self.reg_email = ""
        self.reg_password = ""
        self.reg_password2 = ""
        self.pending_email = email
        if is_mail_configured():
            return rx.redirect("/verificar-email/pendiente")
        self._login(user.id)
        return rx.redirect("/")

    @rx.event
    def forgot_password(self, form_data: dict):
        self.auth_error = ""
        self.forgot_sent = False
        email = (form_data.get("email") or "").strip().lower()
        if not email:
            self.auth_error = "Ingresá tu email."
            return
        if not is_mail_configured():
            self.auth_error = (
                "El envío de emails no está configurado. Contactá al administrador."
            )
            return
        try:
            with rx.session() as session:
                user = session.exec(select(User).where(User.email == email)).first()
                if user and user.activo:
                    issue_password_reset(session, user)
            self.forgot_sent = True
            self.auth_info = (
                "Si el email está registrado, recibirás un enlace para "
                "restablecer la contraseña."
            )
        except Exception:
            self.auth_error = "No se pudo enviar el email. Revisá la configuración Gmail."

    @rx.event
    def resend_verification(self, form_data: dict):
        self.auth_error = ""
        self.auth_info = ""
        email = (form_data.get("email") or self.pending_email or "").strip().lower()
        if not email:
            self.auth_error = "Ingresá tu email."
            return
        if not is_mail_configured():
            self.auth_error = "Gmail no configurado."
            return
        try:
            with rx.session() as session:
                user = session.exec(select(User).where(User.email == email)).first()
                if user is None:
                    self.auth_error = "No encontramos ese email."
                    return
                if user.email_verified:
                    self.auth_info = "Este email ya está verificado. Podés ingresar."
                    return
                issue_verification(session, user)
            self.pending_email = email
            self.auth_info = "Te reenviamos el email de verificación."
        except Exception:
            self.auth_error = "No se pudo enviar el email."

    @rx.event
    def verify_email_from_link(self):
        self._bootstrap()
        self.auth_error = ""
        self.auth_info = ""
        raw = self.token
        if not raw:
            self.auth_error = "Enlace inválido."
            return rx.redirect("/login")
        try:
            with rx.session() as session:
                user = verify_email_token(session, raw)
            if user is None:
                self.auth_error = "El enlace expiró o ya fue usado."
                return rx.redirect("/login")
            self.auth_info = "Email verificado correctamente."
        except Exception:
            self.auth_error = "No se pudo verificar el email."
        return rx.redirect("/login")

    @rx.event
    def load_reset_page(self):
        self._bootstrap()
        self.auth_error = ""
        raw = self.token
        if not raw:
            self.auth_error = "Enlace inválido."
            return
        try:
            with rx.session() as session:
                user = validate_reset_token(session, raw)
            if user is None:
                self.auth_error = "El enlace expiró o ya fue usado."
        except Exception:
            self.auth_error = "No se pudo validar el enlace."

    @rx.event
    def reset_password(self, form_data: dict):
        self.auth_error = ""
        raw = self.token
        password = form_data.get("password") or ""
        password2 = form_data.get("password2") or ""
        if not raw:
            self.auth_error = "Enlace inválido."
            return
        if len(password) < 8:
            self.auth_error = "La contraseña debe tener al menos 8 caracteres."
            return
        if password != password2:
            self.auth_error = "Las contraseñas no coinciden."
            return
        try:
            with rx.session() as session:
                user = consume_token(session, raw, "reset")
                if user is None:
                    self.auth_error = "El enlace expiró o ya fue usado."
                    return
                user.password_hash = User.hash_password(password)
                session.add(user)
                session.commit()
            self.auth_info = "Contraseña actualizada. Ya podés ingresar."
            return rx.redirect("/login")
        except Exception:
            self.auth_error = "No se pudo restablecer la contraseña."
