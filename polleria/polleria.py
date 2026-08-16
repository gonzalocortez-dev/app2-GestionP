"""Aplicación principal de gestión para pollería."""

from __future__ import annotations

import reflex as rx

from polleria.auth.state import AuthState
from polleria.constants import APP_NAME, LOGO_PATH
from polleria.pages.auth_pages import (
    forgot_password_page,
    login_page,
    register_page,
    reset_password_page,
    verify_link_page,
    verify_pending_page,
)
from polleria.pages.dashboard import dashboard_page
from polleria.pages.modules import (
    cash_page,
    expenses_page,
    inventory_page,
    products_page,
    purchases_page,
    reports_page,
    sales_page,
    sellers_page,
    settings_page,
    users_page,
)
from polleria.pages.pos import pos_page
from polleria.states.admin import ReportState, SalesListState, SettingsState, UsersAdminState
from polleria.states.catalog import InventoryState, ProductState, SellerState
from polleria.states.dashboard import DashboardState
from polleria.states.finance import CashState, ExpenseState, PurchaseState
from polleria.states.pos import POSState

app = rx.App(
    head_components=[
        rx.el.link(rel="icon", href=LOGO_PATH, type="image/png"),
        rx.el.link(rel="apple-touch-icon", href=LOGO_PATH),
    ],
)

app.add_page(
    dashboard_page,
    route="/",
    title=f"Dashboard · {APP_NAME}",
    on_load=DashboardState.on_load,
)
app.add_page(
    login_page,
    route="/login",
    title=f"Ingresar · {APP_NAME}",
    image=LOGO_PATH,
    on_load=AuthState.require_guest,
)
app.add_page(
    register_page,
    route="/registro",
    title=f"Registro · {APP_NAME}",
    image=LOGO_PATH,
    on_load=AuthState.require_guest,
)
app.add_page(
    forgot_password_page,
    route="/olvide-contrasena",
    title=f"Recuperar contraseña · {APP_NAME}",
    image=LOGO_PATH,
    on_load=AuthState.require_guest,
)
app.add_page(
    verify_pending_page,
    route="/verificar-email/pendiente",
    title=f"Verificar email · {APP_NAME}",
    image=LOGO_PATH,
    on_load=AuthState.require_guest,
)
app.add_page(
    verify_link_page,
    route="/verificar-email/[token]",
    title=f"Verificar email · {APP_NAME}",
    image=LOGO_PATH,
    on_load=AuthState.verify_email_from_link,
)
app.add_page(
    reset_password_page,
    route="/restablecer-contrasena/[token]",
    title=f"Nueva contraseña · {APP_NAME}",
    image=LOGO_PATH,
    on_load=AuthState.load_reset_page,
)
app.add_page(
    pos_page,
    route="/pos",
    title=f"Punto de Venta · {APP_NAME}",
    on_load=POSState.on_load,
)
app.add_page(
    sales_page,
    route="/ventas",
    title=f"Ventas · {APP_NAME}",
    on_load=SalesListState.on_load,
)
app.add_page(
    products_page,
    route="/productos",
    title=f"Productos · {APP_NAME}",
    on_load=ProductState.on_load,
)
app.add_page(
    inventory_page,
    route="/inventario",
    title=f"Inventario · {APP_NAME}",
    on_load=InventoryState.on_load,
)
app.add_page(
    expenses_page,
    route="/gastos",
    title=f"Gastos · {APP_NAME}",
    on_load=ExpenseState.on_load,
)
app.add_page(
    purchases_page,
    route="/compras",
    title=f"Compras · {APP_NAME}",
    on_load=PurchaseState.on_load,
)
app.add_page(
    sellers_page,
    route="/vendedores",
    title=f"Vendedores · {APP_NAME}",
    on_load=SellerState.on_load,
)
app.add_page(
    cash_page,
    route="/caja",
    title=f"Cierre de caja · {APP_NAME}",
    on_load=CashState.on_load,
)
app.add_page(
    reports_page,
    route="/reportes",
    title=f"Reportes · {APP_NAME}",
    on_load=ReportState.on_load,
)
app.add_page(
    users_page,
    route="/usuarios",
    title=f"Usuarios · {APP_NAME}",
    on_load=UsersAdminState.on_load,
)
app.add_page(
    settings_page,
    route="/configuracion",
    title=f"Configuración · {APP_NAME}",
    on_load=SettingsState.on_load,
)
