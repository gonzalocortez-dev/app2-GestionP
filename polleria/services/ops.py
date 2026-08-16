"""Compras, gastos y movimientos de inventario."""

from __future__ import annotations

from datetime import datetime

from sqlmodel import Session

from polleria.models import Expense, Product, Purchase, PurchaseItem
from polleria.services.core import (
    BusinessError,
    apply_stock,
    audit,
    get_product,
    require_perm,
    safe_commit,
)
from polleria.utils.money import round_money
from polleria.utils.time import now_ar


def register_expense(
    db: Session,
    *,
    actor_id: int,
    actor_role: str,
    categoria: str,
    descripcion: str,
    monto: float,
    fecha: datetime,
    metodo_pago: str,
    observaciones: str = "",
    purchase_id: int | None = None,
) -> Expense:
    require_perm(actor_role, "expenses.manage")
    if monto <= 0:
        raise BusinessError("El importe del gasto debe ser positivo.")
    if not categoria:
        raise BusinessError("Elegí una categoría.")
    expense = Expense(
        categoria=categoria,
        descripcion=descripcion.strip(),
        monto=round_money(monto),
        fecha=fecha,
        metodo_pago=metodo_pago,
        usuario_id=actor_id,
        observaciones=observaciones,
        purchase_id=purchase_id,
    )
    db.add(expense)
    db.flush()
    audit(
        db,
        usuario_id=actor_id,
        accion="expense.create",
        entidad="expense",
        entidad_id=expense.id,
        detalle=f"{categoria} ${monto}",
    )
    safe_commit(db)
    db.refresh(expense)
    return expense


def create_purchase(
    db: Session,
    *,
    actor_id: int,
    actor_role: str,
    proveedor: str,
    items: list[dict],
    fecha: datetime | None = None,
    registrar_gasto: bool = True,
    observaciones: str = "",
    metodo_pago: str = "Efectivo",
) -> Purchase:
    require_perm(actor_role, "purchases.manage")
    if not items:
        raise BusinessError("Agregá al menos un producto a la compra.")
    when = fecha or now_ar()
    total = 0.0
    parsed: list[tuple[Product, float, float, float]] = []
    for raw in items:
        product = get_product(db, int(raw["product_id"]))
        qty = float(raw["cantidad"])
        cost = float(raw["costo_unitario"])
        if qty <= 0 or cost < 0:
            raise BusinessError("Cantidad y costo deben ser válidos.")
        subtotal = round_money(qty * cost)
        total += subtotal
        parsed.append((product, qty, cost, subtotal))

    purchase = Purchase(
        proveedor=proveedor.strip() or "Proveedor",
        fecha=when,
        total=round_money(total),
        usuario_id=actor_id,
        registrar_gasto=registrar_gasto,
        observaciones=observaciones,
    )
    db.add(purchase)
    db.flush()

    for product, qty, cost, subtotal in parsed:
        db.add(
            PurchaseItem(
                purchase_id=purchase.id,
                product_id=product.id,
                cantidad=qty,
                costo_unitario=cost,
                subtotal=subtotal,
            )
        )
        old_stock = product.stock or 0
        old_cost = product.costo or 0
        if old_stock > 0:
            product.costo = round_money((old_stock * old_cost + qty * cost) / (old_stock + qty))
        else:
            product.costo = round_money(cost)
        apply_stock(
            db,
            product=product,
            tipo="compra",
            cantidad=qty,
            usuario_id=actor_id,
            motivo=f"Compra {proveedor}",
            referencia=f"compra:{purchase.id}",
            fecha=when,
        )

    if registrar_gasto:
        db.add(
            Expense(
                categoria="Compra de mercadería",
                descripcion=f"Compra a {proveedor or 'proveedor'}",
                monto=round_money(total),
                fecha=when,
                metodo_pago=metodo_pago,
                usuario_id=actor_id,
                observaciones=observaciones,
                purchase_id=purchase.id,
            )
        )

    audit(
        db,
        usuario_id=actor_id,
        accion="purchase.create",
        entidad="purchase",
        entidad_id=purchase.id,
        detalle=f"Compra total={total}",
    )
    safe_commit(db)
    db.refresh(purchase)
    return purchase


def move_inventory(
    db: Session,
    *,
    actor_id: int,
    actor_role: str,
    product_id: int,
    tipo: str,
    cantidad: float,
    motivo: str,
) -> Product:
    require_perm(actor_role, "inventory.manage")
    if cantidad == 0:
        raise BusinessError("La cantidad no puede ser cero.")
    product = get_product(db, product_id)
    apply_stock(
        db,
        product=product,
        tipo=tipo,
        cantidad=cantidad,
        usuario_id=actor_id,
        motivo=motivo,
        referencia="manual",
        fecha=now_ar(),
    )
    audit(
        db,
        usuario_id=actor_id,
        accion="inventory.move",
        entidad="product",
        entidad_id=product.id,
        detalle=f"{tipo} {cantidad} {product.nombre}",
    )
    safe_commit(db)
    db.refresh(product)
    return product
