"""Usuarios, configuración, reportes y listado de ventas."""

from __future__ import annotations

import reflex as rx
from sqlmodel import select

from polleria.auth.state import AuthState
from polleria.constants import ROLE_LABELS
from polleria.models import BusinessSettings, User
from polleria.schemas import (
    ExpenseRow,
    ReportProductRow,
    ReportSellerRow,
    SaleRow,
    UserRow,
)
from polleria.services.core import BusinessError, PermissionDenied, safe_commit
from polleria.services.deletes import delete_sale, delete_user
from polleria.services import queries
from polleria.utils.money import money
from polleria.utils.time import format_dt, iso_date, period_range, today_ar


class SalesListState(AuthState):
    items: list[SaleRow] = []
    period: str = "mes"
    metodo_pago: str = ""
    vendedor_label: str = "Todos"
    vendedor_options: list[str] = ["Todos"]

    @rx.event
    def on_load(self):
        if redir := self._redirect_guest():
            return redir
        if not self._has("sales.view_own"):
            return self._home_redirect()
        self.reload()

    @rx.event
    def reload(self):
        start, end = period_range(self.period)
        only = None if self.can_view_all_sales else self.authenticated_user.id
        vendedor_id = None
        if self.vendedor_label != "Todos":
            try:
                vendedor_id = int(self.vendedor_label.split(" · ", 1)[0])
            except ValueError:
                vendedor_id = None
        with rx.session() as db:
            users = db.exec(select(User).where(User.activo == True).order_by(User.nombre)).all()  # noqa: E712
            self.vendedor_options = ["Todos"] + [f"{u.id} · {u.nombre_completo}" for u in users]
            self.items = [
                SaleRow(**row)
                for row in queries.report_sales(
                    db,
                    start,
                    end,
                    vendedor_id=vendedor_id,
                    metodo_pago=self.metodo_pago,
                    only_vendedor=only,
                )
            ]

    @rx.event
    def set_period(self, value: str):
        self.period = value
        self.reload()

    @rx.event
    def set_metodo(self, value: str):
        self.metodo_pago = "" if value == "Todos" else value
        self.reload()

    @rx.event
    def set_vendedor(self, value: str):
        self.vendedor_label = value
        self.reload()

    @rx.event
    def delete_item(self, sale_id: int):
        try:
            with rx.session() as db:
                delete_sale(
                    db,
                    actor_id=self.authenticated_user.id,
                    actor_role=self.authenticated_user.role,
                    sale_id=sale_id,
                )
        except (BusinessError, PermissionDenied) as exc:
            return rx.toast.error(str(exc))
        self.reload()
        return rx.toast.success("Venta eliminada")


class ReportState(AuthState):
    tab: str = "ventas"
    start: str = ""
    end: str = ""
    metodo_pago: str = ""
    sales: list[SaleRow] = []
    expenses: list[ExpenseRow] = []
    products: list[ReportProductRow] = []
    sellers: list[ReportSellerRow] = []

    @rx.event
    def on_load(self):
        if redir := self._redirect_guest():
            return redir
        if not self._has("reports.view"):
            return self._home_redirect()
        self.start = iso_date(today_ar().replace(day=1))
        self.end = iso_date()
        self.reload()

    @rx.event
    def set_tab(self, tab: str):
        self.tab = tab

    @rx.event
    def reload(self):
        start, end = period_range("personalizado", self.start, self.end)
        with rx.session() as db:
            self.sales = [
                SaleRow(**r)
                for r in queries.report_sales(db, start, end, metodo_pago=self.metodo_pago)
            ]
            self.expenses = [ExpenseRow(**r) for r in queries.report_expenses(db, start, end)]
            self.products = [ReportProductRow(**r) for r in queries.report_products(db, start, end)]
            self.sellers = [ReportSellerRow(**r) for r in queries.report_sellers(db, start, end)]


class UsersAdminState(AuthState):
    items: list[UserRow] = []
    dialog_open: bool = False
    editing_id: int = 0
    form_nombre: str = ""
    form_apellido: str = ""
    form_email: str = ""
    form_password: str = ""
    form_role: str = "vendedor"
    form_activo: bool = True

    @rx.event
    def on_load(self):
        if redir := self._redirect_guest():
            return redir
        if not self._has("users.manage"):
            return self._home_redirect()
        self.reload()

    @rx.event
    def reload(self):
        with rx.session() as db:
            users = db.exec(select(User).order_by(User.nombre)).all()
        self.items = [
            UserRow(
                id=u.id or 0,
                nombre=u.nombre_completo,
                email=u.email,
                role=u.role,
                role_label=ROLE_LABELS.get(u.role, u.role),
                activo=u.activo,
                last_activity=format_dt(u.last_activity) if u.last_activity else "—",
            )
            for u in users
        ]

    @rx.event
    def open_new(self):
        self.editing_id = 0
        self.form_nombre = ""
        self.form_apellido = ""
        self.form_email = ""
        self.form_password = ""
        self.form_role = "vendedor"
        self.form_activo = True
        self.dialog_open = True

    @rx.event
    def open_edit(self, user_id: int):
        with rx.session() as db:
            user = db.get(User, user_id)
        if user is None:
            return
        self.editing_id = user.id or 0
        self.form_nombre = user.nombre
        self.form_apellido = user.apellido
        self.form_email = user.email
        self.form_password = ""
        self.form_role = user.role
        self.form_activo = user.activo
        self.dialog_open = True

    @rx.event
    def close_dialog(self):
        self.dialog_open = False

    @rx.event
    def set_dialog_open(self, value: bool):
        self.dialog_open = value

    @rx.event
    def save(self):
        try:
            self._require("users.manage")
            if self.editing_id and self.editing_id == self.authenticated_user.id:
                if self.form_role != self.authenticated_user.role:
                    raise BusinessError("No podés cambiar tu propio rol.")
            email = self.form_email.strip().lower()
            if not self.form_nombre.strip() or not email:
                raise BusinessError("Nombre y email son obligatorios.")
            if self.form_role not in ROLE_LABELS:
                raise BusinessError("Rol inválido.")
            with rx.session() as db:
                if self.editing_id:
                    user = db.get(User, self.editing_id)
                    if user is None:
                        raise BusinessError("Usuario no encontrado.")
                else:
                    if not self.form_password or len(self.form_password) < 8:
                        raise BusinessError("La contraseña debe tener al menos 8 caracteres.")
                    if db.exec(select(User).where(User.email == email)).first():
                        raise BusinessError("Ese email ya está en uso.")
                    user = User(password_hash=User.hash_password(self.form_password))
                user.nombre = self.form_nombre.strip()
                user.apellido = self.form_apellido.strip()
                user.email = email
                user.role = self.form_role
                user.activo = self.form_activo
                if self.form_password:
                    if len(self.form_password) < 8:
                        raise BusinessError("La contraseña debe tener al menos 8 caracteres.")
                    user.password_hash = User.hash_password(self.form_password)
                db.add(user)
                safe_commit(db)
        except (BusinessError, PermissionDenied) as exc:
            return rx.toast.error(str(exc))
        self.dialog_open = False
        self.reload()
        return rx.toast.success("Usuario guardado")

    @rx.event
    def toggle_active(self, user_id: int):
        if user_id == self.authenticated_user.id:
            return rx.toast.error("No podés desactivar tu propio usuario.")
        try:
            self._require("users.manage")
            with rx.session() as db:
                user = db.get(User, user_id)
                if user is None:
                    raise BusinessError("Usuario no encontrado.")
                user.activo = not user.activo
                db.add(user)
                safe_commit(db)
        except (BusinessError, PermissionDenied) as exc:
            return rx.toast.error(str(exc))
        self.reload()

    @rx.event
    def delete_item(self, user_id: int):
        try:
            with rx.session() as db:
                result = delete_user(
                    db,
                    actor_id=self.authenticated_user.id,
                    actor_role=self.authenticated_user.role,
                    user_id=user_id,
                )
        except (BusinessError, PermissionDenied) as exc:
            return rx.toast.error(str(exc))
        self.reload()
        if result == "desactivado":
            return rx.toast.success("Usuario desactivado: tiene movimientos cargados.")
        return rx.toast.success("Usuario eliminado")


class SettingsState(AuthState):
    nombre_comercio: str = ""
    slogan: str = ""
    telefono: str = ""
    direccion: str = ""
    cuit: str = ""
    moneda: str = "ARS"
    simbolo: str = "$"
    logo_url: str = ""

    @rx.event
    def on_load(self):
        if redir := self._redirect_guest():
            return redir
        if not self._has("settings.manage"):
            return self._home_redirect()
        self.reload()

    @rx.event
    def reload(self):
        with rx.session() as db:
            row = db.exec(select(BusinessSettings)).first()
            if row is None:
                row = BusinessSettings()
                db.add(row)
                db.commit()
                db.refresh(row)
        self.nombre_comercio = row.nombre_comercio
        self.slogan = row.slogan
        self.telefono = row.telefono
        self.direccion = row.direccion
        self.cuit = row.cuit
        self.moneda = row.moneda
        self.simbolo = row.simbolo_moneda
        self.logo_url = row.logo_url
        self.business_name = row.nombre_comercio

    @rx.event
    def save(self):
        try:
            self._require("settings.manage")
            if not self.nombre_comercio.strip():
                raise BusinessError("El nombre del comercio es obligatorio.")
            with rx.session() as db:
                row = db.exec(select(BusinessSettings)).first()
                if row is None:
                    row = BusinessSettings()
                row.nombre_comercio = self.nombre_comercio.strip()
                row.slogan = self.slogan.strip()
                row.telefono = self.telefono.strip()
                row.direccion = self.direccion.strip()
                row.cuit = self.cuit.strip()
                row.moneda = self.moneda.strip() or "ARS"
                row.simbolo_moneda = self.simbolo.strip() or "$"
                row.logo_url = self.logo_url.strip()
                db.add(row)
                safe_commit(db)
            self.business_name = self.nombre_comercio.strip()
        except (BusinessError, PermissionDenied) as exc:
            return rx.toast.error(str(exc))
        return rx.toast.success("Configuración guardada")
