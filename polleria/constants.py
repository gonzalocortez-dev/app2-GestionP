"""Constantes de negocio: roles, pagos, categorías y navegación."""

from __future__ import annotations

APP_NAME = "La Fábrica del Pollo"
APP_TAGLINE = "Gestión integral"
LOGO_PATH = "/logo.png"

ROLES = ("admin", "supervisor", "vendedor")
ROLE_LABELS = {
    "admin": "Administrador",
    "supervisor": "Supervisor",
    "vendedor": "Vendedor",
}

PAYMENT_METHODS = (
    "Efectivo",
    "Transferencia",
    "Débito",
    "Crédito",
    "Mercado Pago",
    "Otro",
)

BRANCHES = (
    "La Fábrica del Pollo",
    "La 23",
    "Don Juliano",
)

# Contenido fijo de una caja de pollo de 20 kg. No se edita desde la UI.
CHICKEN_BOX_CUTS: tuple[tuple[str, float], ...] = (
    ("Patamuslo", 7.615),
    ("Alitas", 3.240),
    ("Pechuga", 6.040),
    ("Menudo", 1.530),
    ("Puchero", 1.430),
)
CHICKEN_BOX_COUNTS = tuple(str(n) for n in range(1, 11))
CHICKEN_CUT_ALIASES: dict[str, frozenset[str]] = {
    "Patamuslo": frozenset({"patamuslo", "pata muslo", "pata y muslo"}),
    "Alitas": frozenset({"alitas", "alita"}),
    "Pechuga": frozenset({"pechuga"}),
    "Menudo": frozenset({"menudo", "menudos", "menudencias"}),
    "Puchero": frozenset({"puchero"}),
}

PRODUCT_CATEGORIES = (
    "Pollo",
    "Cortes",
    "Elaborados",
    "Menudencias",
    "Otros",
)

UNITS = ("Unidad", "Kg", "Gramos", "Bandeja")

EXPENSE_CATEGORIES = (
    "Luz",
    "Agua",
    "Gas",
    "Alquiler",
    "Sueldos",
    "Empleado",
    "Combustible",
    "Mantenimiento",
    "Compra de mercadería",
    "Publicidad",
    "Impuestos",
    "Otros",
)

INVENTORY_TYPES = ("compra", "venta", "ajuste", "merma", "devolucion")
INVENTORY_TYPE_LABELS = {
    "compra": "Compra",
    "venta": "Venta",
    "ajuste": "Ajuste",
    "merma": "Merma",
    "devolucion": "Devolución",
}

SALE_STATUSES = ("completada", "anulada")

PERIODS = (
    ("hoy", "Hoy"),
    ("ayer", "Ayer"),
    ("semana", "Esta semana"),
    ("mes", "Este mes"),
    ("mes_anterior", "Mes anterior"),
    ("personalizado", "Personalizado"),
)

PERIOD_LABELS = dict(PERIODS)

NAV_ITEMS = (
    {"label": "Dashboard", "href": "/", "icon": "layout-dashboard", "perm": "dashboard"},
    {"label": "Punto de Venta", "href": "/pos", "icon": "shopping-cart", "perm": "pos"},
    {"label": "Ventas", "href": "/ventas", "icon": "receipt", "perm": "sales.view_own"},
    {"label": "Productos", "href": "/productos", "icon": "drumstick", "perm": "products.view"},
    {"label": "Inventario", "href": "/inventario", "icon": "warehouse", "perm": "inventory.view"},
    {"label": "Gastos", "href": "/gastos", "icon": "wallet", "perm": "expenses.manage"},
    {"label": "Compras", "href": "/compras", "icon": "package-plus", "perm": "purchases.view"},
    {"label": "Vendedores", "href": "/vendedores", "icon": "users", "perm": "sellers.view"},
    {"label": "Cierre de caja", "href": "/caja", "icon": "landmark", "perm": "cash.close"},
    {"label": "Reportes", "href": "/reportes", "icon": "chart-column", "perm": "reports.view"},
    {"label": "Usuarios", "href": "/usuarios", "icon": "shield", "perm": "users.manage"},
    {"label": "Configuración", "href": "/configuracion", "icon": "settings", "perm": "settings.manage"},
)

CHART_COLORS = ["#ea580c", "#f59e0b", "#16a34a", "#2563eb", "#7c3aed", "#db2777", "#0d9488"]
