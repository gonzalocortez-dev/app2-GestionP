"""Capa de datos y reglas de negocio. Las operaciones sensibles validan permisos aquí."""

from __future__ import annotations

from datetime import datetime

import reflex as rx
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, select

from polleria.auth.permissions import has_permission
from polleria.models import AuditLog, InventoryMovement, Product
from polleria.utils.time import now_ar


class PermissionDenied(Exception):
    pass


class BusinessError(Exception):
    pass


class DatabaseUnavailable(Exception):
    pass


def require_perm(role: str | None, permission: str) -> None:
    if not has_permission(role, permission):
        raise PermissionDenied("No tenés permisos para esta operación.")


def session() -> Session:
    return rx.session()


def audit(
    db: Session,
    *,
    usuario_id: int | None,
    accion: str,
    entidad: str = "",
    entidad_id: int | None = None,
    detalle: str = "",
) -> None:
    db.add(
        AuditLog(
            usuario_id=usuario_id,
            accion=accion,
            entidad=entidad,
            entidad_id=entidad_id,
            detalle=detalle[:500],
        )
    )


def apply_stock(
    db: Session,
    *,
    product: Product,
    tipo: str,
    cantidad: float,
    usuario_id: int,
    motivo: str = "",
    referencia: str = "",
    sucursal: str = "",
    fecha: datetime | None = None,
) -> None:
    from polleria.services.stock import get_or_create_branch_stock, sync_product_total

    branch = (sucursal or "").strip()
    if not branch:
        raise BusinessError("Seleccioná la sucursal para mover stock.")

    if tipo == "ajuste":
        delta = cantidad
    elif tipo in {"compra", "devolucion"}:
        delta = abs(cantidad)
    else:
        delta = -abs(cantidad)

    row = get_or_create_branch_stock(db, product.id or 0, branch)
    nuevo = round((row.cantidad or 0) + delta, 3)
    if nuevo < -0.0001 and tipo == "venta":
        raise BusinessError(
            f"Stock insuficiente de {product.nombre} en {branch}. "
            f"Disponible: {row.cantidad}"
        )
    if tipo == "ajuste":
        row.cantidad = nuevo
    else:
        row.cantidad = max(nuevo, 0)
    db.add(row)
    sync_product_total(db, product)
    db.add(
        InventoryMovement(
            product_id=product.id,
            tipo=tipo,
            cantidad=cantidad,
            motivo=motivo,
            usuario_id=usuario_id,
            fecha=fecha or now_ar(),
            referencia=referencia,
            sucursal=branch,
        )
    )


def safe_commit(db: Session) -> None:
    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise DatabaseUnavailable("No se pudo guardar en la base de datos.") from exc


def get_product(db: Session, product_id: int) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise BusinessError("Producto no encontrado.")
    return product
