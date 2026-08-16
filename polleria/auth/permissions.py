"""Permisos por rol. Agregar un rol nuevo solo requiere una entrada aquí."""

from __future__ import annotations

from polleria.constants import ROLES

ADMIN = "admin"
SUPERVISOR = "supervisor"
VENDEDOR = "vendedor"

# Cada permiso lista los roles que lo tienen. El admin tiene todos implícitamente.
_PERMISSIONS: dict[str, frozenset[str]] = {
    "dashboard": frozenset({ADMIN, SUPERVISOR, VENDEDOR}),
    "pos": frozenset({ADMIN, SUPERVISOR, VENDEDOR}),
    "sales.view_own": frozenset({ADMIN, SUPERVISOR, VENDEDOR}),
    "sales.view_all": frozenset({ADMIN, SUPERVISOR}),
    "products.view": frozenset({ADMIN, SUPERVISOR, VENDEDOR}),
    "products.manage": frozenset({ADMIN}),
    "inventory.view": frozenset({ADMIN, SUPERVISOR}),
    "inventory.manage": frozenset({ADMIN}),
    "expenses.manage": frozenset({ADMIN, SUPERVISOR}),
    "purchases.view": frozenset({ADMIN, SUPERVISOR}),
    "purchases.manage": frozenset({ADMIN}),
    "sellers.view": frozenset({ADMIN, SUPERVISOR}),
    "sellers.manage": frozenset({ADMIN}),
    "reports.view": frozenset({ADMIN, SUPERVISOR}),
    "users.manage": frozenset({ADMIN}),
    "settings.manage": frozenset({ADMIN}),
    "cash.close": frozenset({ADMIN, SUPERVISOR, VENDEDOR}),
    "profits.view": frozenset({ADMIN, SUPERVISOR}),
}


def has_permission(role: str | None, permission: str) -> bool:
    if not role:
        return False
    if role == ADMIN:
        return True
    allowed = _PERMISSIONS.get(permission)
    if allowed is None:
        return False
    return role in allowed


def known_roles() -> tuple[str, ...]:
    return ROLES
