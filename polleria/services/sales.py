"""Registro transaccional de ventas detalladas y rápidas."""

from __future__ import annotations

from datetime import datetime

from sqlmodel import Session, select

from polleria.models import Product, Sale, SaleItem, User
from polleria.services.core import (
    BusinessError,
    apply_stock,
    audit,
    require_perm,
    safe_commit,
)
from polleria.utils.money import round_money
from polleria.utils.time import now_ar


def create_detailed_sale(
    db: Session,
    *,
    actor_id: int,
    actor_role: str,
    vendedor_id: int,
    items: list[dict],
    metodo_pago: str,
    descuento: float = 0.0,
    observacion: str = "",
    fecha: datetime | None = None,
) -> Sale:
    require_perm(actor_role, "pos")
    if not items:
        raise BusinessError("Agregá al menos un producto.")
    if descuento < 0:
        raise BusinessError("El descuento no puede ser negativo.")

    vendedor = db.get(User, vendedor_id)
    if vendedor is None or not vendedor.activo:
        raise BusinessError("Seleccioná un vendedor activo.")

    when = fecha or now_ar()
    sale_items: list[SaleItem] = []
    subtotal = 0.0
    costo_total = 0.0

    for raw in items:
        product = db.get(Product, int(raw["product_id"]))
        if product is None or not product.activo:
            raise BusinessError("Hay un producto inválido en el carrito.")
        qty = float(raw["cantidad"])
        if qty <= 0:
            raise BusinessError(f"La cantidad de {product.nombre} debe ser positiva.")
        precio = float(raw.get("precio_unitario", product.precio_venta))
        if precio < 0:
            raise BusinessError("El precio no puede ser negativo.")
        costo = float(product.costo or 0)
        line = round_money(precio * qty)
        subtotal += line
        costo_total += round_money(costo * qty)
        sale_items.append(
            SaleItem(
                product_id=product.id,
                cantidad=qty,
                precio_unitario=precio,
                costo_unitario=costo,
                subtotal=line,
            )
        )

    if descuento > subtotal:
        raise BusinessError("El descuento no puede ser mayor al subtotal.")

    total = round_money(subtotal - descuento)
    costo_total = round_money(costo_total)
    ganancia = round_money(total - costo_total) if costo_total > 0 else round_money(total - costo_total)

    sale = Sale(
        vendedor_id=vendedor_id,
        created_by=actor_id,
        fecha=when,
        subtotal=round_money(subtotal),
        descuento=round_money(descuento),
        total=total,
        costo_total=costo_total,
        ganancia=ganancia,
        tiene_costo=True,
        is_quick=False,
        metodo_pago=metodo_pago,
        estado="completada",
        observacion=observacion,
    )
    db.add(sale)
    db.flush()

    for item in sale_items:
        item.sale_id = sale.id
        db.add(item)
        product = get_locked_product(db, item.product_id)
        apply_stock(
            db,
            product=product,
            tipo="venta",
            cantidad=item.cantidad,
            usuario_id=actor_id,
            motivo="Venta",
            referencia=f"venta:{sale.id}",
            fecha=when,
        )

    audit(
        db,
        usuario_id=actor_id,
        accion="sale.create",
        entidad="sale",
        entidad_id=sale.id,
        detalle=f"Venta #{sale.id} total={total} pago={metodo_pago}",
    )
    safe_commit(db)
    db.refresh(sale)
    return sale


def create_quick_sale(
    db: Session,
    *,
    actor_id: int,
    actor_role: str,
    vendedor_id: int,
    importe: float,
    metodo_pago: str,
    observacion: str = "",
    fecha: datetime | None = None,
) -> Sale:
    require_perm(actor_role, "pos")
    if importe <= 0:
        raise BusinessError("El importe debe ser mayor a cero.")
    vendedor = db.get(User, vendedor_id)
    if vendedor is None or not vendedor.activo:
        raise BusinessError("Seleccioná un vendedor activo.")

    when = fecha or now_ar()
    sale = Sale(
        vendedor_id=vendedor_id,
        created_by=actor_id,
        fecha=when,
        subtotal=round_money(importe),
        descuento=0,
        total=round_money(importe),
        costo_total=0,
        ganancia=0,
        tiene_costo=False,
        is_quick=True,
        metodo_pago=metodo_pago,
        estado="completada",
        observacion=observacion,
    )
    db.add(sale)
    db.flush()
    audit(
        db,
        usuario_id=actor_id,
        accion="sale.quick",
        entidad="sale",
        entidad_id=sale.id,
        detalle=f"Venta rápida #{sale.id} total={importe}",
    )
    safe_commit(db)
    db.refresh(sale)
    return sale


def get_locked_product(db: Session, product_id: int) -> Product:
    product = db.exec(select(Product).where(Product.id == product_id)).first()
    if product is None:
        raise BusinessError("Producto no encontrado.")
    return product
