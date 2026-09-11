"""Borrado de registros cargados. Solo administradores."""

from __future__ import annotations

from sqlmodel import Session, select

from polleria.models import (
    AuthSession,
    CashRegisterClosure,
    EmailToken,
    Expense,
    InventoryMovement,
    Product,
    Purchase,
    PurchaseItem,
    Sale,
    SaleItem,
    User,
)
from polleria.services.core import BusinessError, audit, require_perm, safe_commit
from polleria.services.stock import get_or_create_branch_stock, sync_product_total


def _require_delete(role: str) -> None:
    require_perm(role, "records.delete")


def delete_sale(db: Session, *, actor_id: int, actor_role: str, sale_id: int) -> None:
    _require_delete(actor_role)
    sale = db.get(Sale, sale_id)
    if sale is None:
        raise BusinessError("Venta no encontrada.")
    items = db.exec(select(SaleItem).where(SaleItem.sale_id == sale_id)).all()
    branch = (sale.sucursal or "").strip()
    for item in items:
        product = db.get(Product, item.product_id)
        if product is not None and branch:
            row = get_or_create_branch_stock(db, product.id or 0, branch)
            row.cantidad = round((row.cantidad or 0) + item.cantidad, 3)
            db.add(row)
            sync_product_total(db, product)
        db.delete(item)
    for move in db.exec(
        select(InventoryMovement).where(InventoryMovement.referencia == f"venta:{sale_id}")
    ).all():
        db.delete(move)
    db.delete(sale)
    audit(
        db,
        usuario_id=actor_id,
        accion="sale.delete",
        entidad="sale",
        entidad_id=sale_id,
        detalle=f"Eliminó venta #{sale_id}",
    )
    safe_commit(db)


def delete_expense(db: Session, *, actor_id: int, actor_role: str, expense_id: int) -> None:
    _require_delete(actor_role)
    expense = db.get(Expense, expense_id)
    if expense is None:
        raise BusinessError("Gasto no encontrado.")
    db.delete(expense)
    audit(
        db,
        usuario_id=actor_id,
        accion="expense.delete",
        entidad="expense",
        entidad_id=expense_id,
        detalle=f"Eliminó gasto {expense.categoria}",
    )
    safe_commit(db)


def delete_purchase(db: Session, *, actor_id: int, actor_role: str, purchase_id: int) -> None:
    _require_delete(actor_role)
    purchase = db.get(Purchase, purchase_id)
    if purchase is None:
        raise BusinessError("Compra no encontrada.")
    items = db.exec(select(PurchaseItem).where(PurchaseItem.purchase_id == purchase_id)).all()
    branch = (purchase.sucursal or "").strip()
    if not branch:
        move = db.exec(
            select(InventoryMovement).where(
                InventoryMovement.referencia == f"compra:{purchase_id}"
            )
        ).first()
        branch = (move.sucursal if move else "") or ""
    for item in items:
        product = db.get(Product, item.product_id)
        if product is not None:
            if branch:
                row = get_or_create_branch_stock(db, product.id or 0, branch)
                nuevo = round((row.cantidad or 0) - item.cantidad, 3)
                if nuevo < -0.0001:
                    raise BusinessError(
                        f"No se puede eliminar: el stock de {product.nombre} "
                        f"en {branch} ya se usó."
                    )
                row.cantidad = max(nuevo, 0)
                db.add(row)
                sync_product_total(db, product)
            else:
                nuevo = round((product.stock or 0) - item.cantidad, 3)
                if nuevo < -0.0001:
                    raise BusinessError(
                        f"No se puede eliminar: el stock de {product.nombre} ya se usó."
                    )
                product.stock = max(nuevo, 0)
                db.add(product)
        db.delete(item)
    for move in db.exec(
        select(InventoryMovement).where(
            InventoryMovement.referencia == f"compra:{purchase_id}"
        )
    ).all():
        db.delete(move)
    for expense in db.exec(select(Expense).where(Expense.purchase_id == purchase_id)).all():
        db.delete(expense)
    db.delete(purchase)
    audit(
        db,
        usuario_id=actor_id,
        accion="purchase.delete",
        entidad="purchase",
        entidad_id=purchase_id,
        detalle=f"Eliminó compra #{purchase_id}",
    )
    safe_commit(db)


def delete_product(db: Session, *, actor_id: int, actor_role: str, product_id: int) -> str:
    _require_delete(actor_role)
    product = db.get(Product, product_id)
    if product is None:
        raise BusinessError("Producto no encontrado.")
    used = (
        db.exec(select(SaleItem).where(SaleItem.product_id == product_id).limit(1)).first()
        or db.exec(
            select(PurchaseItem).where(PurchaseItem.product_id == product_id).limit(1)
        ).first()
        or db.exec(
            select(InventoryMovement)
            .where(InventoryMovement.product_id == product_id)
            .limit(1)
        ).first()
    )
    if used:
        product.activo = False
        db.add(product)
        audit(
            db,
            usuario_id=actor_id,
            accion="product.deactivate",
            entidad="product",
            entidad_id=product_id,
            detalle=f"Desactivó {product.nombre} (tiene movimientos)",
        )
        safe_commit(db)
        return "desactivado"
    db.delete(product)
    audit(
        db,
        usuario_id=actor_id,
        accion="product.delete",
        entidad="product",
        entidad_id=product_id,
        detalle=f"Eliminó {product.nombre}",
    )
    safe_commit(db)
    return "eliminado"


def delete_user(db: Session, *, actor_id: int, actor_role: str, user_id: int) -> str:
    _require_delete(actor_role)
    if user_id == actor_id:
        raise BusinessError("No podés eliminar tu propio usuario.")
    user = db.get(User, user_id)
    if user is None:
        raise BusinessError("Usuario no encontrado.")
    if user.role == "admin":
        other_admins = db.exec(
            select(User).where(User.role == "admin", User.id != user_id, User.activo == True)  # noqa: E712
        ).first()
        if other_admins is None:
            raise BusinessError("No se puede eliminar al único administrador.")
    has_data = (
        db.exec(select(Sale).where(Sale.vendedor_id == user_id).limit(1)).first()
        or db.exec(select(Sale).where(Sale.created_by == user_id).limit(1)).first()
        or db.exec(select(Expense).where(Expense.usuario_id == user_id).limit(1)).first()
        or db.exec(select(Purchase).where(Purchase.usuario_id == user_id).limit(1)).first()
        or db.exec(
            select(InventoryMovement).where(InventoryMovement.usuario_id == user_id).limit(1)
        ).first()
        or db.exec(
            select(CashRegisterClosure)
            .where(CashRegisterClosure.usuario_id == user_id)
            .limit(1)
        ).first()
    )
    for row in db.exec(select(AuthSession).where(AuthSession.user_id == user_id)).all():
        db.delete(row)
    for row in db.exec(select(EmailToken).where(EmailToken.user_id == user_id)).all():
        db.delete(row)
    if has_data:
        user.activo = False
        db.add(user)
        audit(
            db,
            usuario_id=actor_id,
            accion="user.deactivate",
            entidad="user",
            entidad_id=user_id,
            detalle=f"Desactivó {user.email} (tiene movimientos)",
        )
        safe_commit(db)
        return "desactivado"
    db.delete(user)
    audit(
        db,
        usuario_id=actor_id,
        accion="user.delete",
        entidad="user",
        entidad_id=user_id,
        detalle=f"Eliminó {user.email}",
    )
    safe_commit(db)
    return "eliminado"
