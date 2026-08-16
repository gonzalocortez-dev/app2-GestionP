"""Inicialización de datos. Producción: solo configuración del comercio."""

from __future__ import annotations

import os
import random
from datetime import timedelta

import reflex as rx
from sqlmodel import select

from polleria.models import (
    BusinessSettings,
    Expense,
    InventoryMovement,
    Product,
    Sale,
    SaleItem,
    User,
)
from polleria.utils.money import round_money
from polleria.utils.time import now_ar, start_of_day, today_ar

DEMO_EMAILS = (
    "admin@polleria.com",
    "vendedor@polleria.com",
    "supervisor@polleria.com",
)

PRODUCTS = [
    ("Pollo entero", "Pollo fresco entero", "Pollo", "Unidad", 8500, 5500, 42, 8),
    ("Pollo trozado", "Pollo trozado en 8 piezas", "Pollo", "Unidad", 8900, 5700, 28, 6),
    ("Pechuga", "Pechuga de pollo", "Cortes", "Kg", 9200, 6100, 35.5, 8),
    ("Muslo", "Muslo de pollo", "Cortes", "Kg", 6800, 4300, 40.0, 10),
    ("Alitas", "Alitas de pollo", "Cortes", "Kg", 5200, 3100, 22.0, 6),
    ("Menudos", "Menudencias", "Menudencias", "Kg", 2800, 1400, 18.0, 4),
    ("Milanesa de pollo", "Milanesa lista para freír", "Elaborados", "Kg", 9800, 6400, 16.0, 4),
    ("Hamburguesa", "Hamburguesa de pollo", "Elaborados", "Unidad", 1400, 750, 80, 20),
]


def should_seed_demo() -> bool:
    flag = os.getenv("SEED_DEMO", "false").strip().lower()
    return flag in {"1", "true", "yes", "si", "sí"}


def bootstrap_if_empty() -> None:
    """Crea la configuración del comercio si no existe. No crea usuarios."""
    with rx.session() as db:
        settings = db.exec(select(BusinessSettings).limit(1)).first()
        if settings:
            return
        db.add(
            BusinessSettings(
                nombre_comercio="La Fábrica del Pollo",
                slogan="Pollo fresco todos los días",
                telefono="",
                direccion="",
                moneda="ARS",
                simbolo_moneda="$",
            )
        )
        db.commit()


def seed_if_empty() -> None:
    bootstrap_if_empty()
    if not should_seed_demo():
        return
    with rx.session() as db:
        existing = db.exec(select(User).limit(1)).first()
        if existing:
            return
        _seed_demo(db)


def _seed_demo(db) -> None:
    admin = User(
        nombre="Ana",
        apellido="Admin",
        email="admin@polleria.com",
        password_hash=User.hash_password("Polleria123!"),
        role="admin",
        activo=True,
    )
    seller = User(
        nombre="Luis",
        apellido="Vendedor",
        email="vendedor@polleria.com",
        password_hash=User.hash_password("Polleria123!"),
        role="vendedor",
        activo=True,
    )
    supervisor = User(
        nombre="Marta",
        apellido="Supervisor",
        email="supervisor@polleria.com",
        password_hash=User.hash_password("Polleria123!"),
        role="supervisor",
        activo=True,
    )
    db.add(admin)
    db.add(seller)
    db.add(supervisor)
    db.commit()
    db.refresh(admin)
    db.refresh(seller)
    db.refresh(supervisor)

    products: list[Product] = []
    for nombre, desc, cat, unidad, precio, costo, stock, minimo in PRODUCTS:
        product = Product(
            nombre=nombre,
            descripcion=desc,
            categoria=cat,
            unidad_medida=unidad,
            precio_venta=precio,
            costo=costo,
            stock=stock,
            stock_minimo=minimo,
            activo=True,
        )
        db.add(product)
        products.append(product)
    db.commit()
    for product in products:
        db.refresh(product)

    rng = random.Random(42)
    sellers = [admin, seller, supervisor]
    methods = ["Efectivo", "Transferencia", "Débito", "Crédito", "Mercado Pago"]
    today = today_ar()

    for day_offset in range(20, -1, -1):
        day = today - timedelta(days=day_offset)
        n_sales = rng.randint(4, 9)
        for _ in range(n_sales):
            who = rng.choice(sellers)
            hour = rng.randint(9, 20)
            minute = rng.choice([0, 10, 15, 30, 45])
            when = start_of_day(day).replace(hour=hour, minute=minute)
            if rng.random() < 0.18:
                amount = rng.choice([5000, 8000, 12000, 15000, 20000])
                db.add(
                    Sale(
                        vendedor_id=who.id,
                        created_by=who.id,
                        fecha=when,
                        subtotal=amount,
                        descuento=0,
                        total=amount,
                        costo_total=0,
                        ganancia=0,
                        tiene_costo=False,
                        is_quick=True,
                        metodo_pago=rng.choice(methods),
                        estado="completada",
                        observacion="Venta rápida de demostración",
                    )
                )
                continue

            chosen = rng.sample(products, k=rng.randint(1, 3))
            sale = Sale(
                vendedor_id=who.id,
                created_by=who.id,
                fecha=when,
                subtotal=0,
                descuento=0,
                total=0,
                costo_total=0,
                ganancia=0,
                tiene_costo=True,
                is_quick=False,
                metodo_pago=rng.choice(methods),
                estado="completada",
            )
            db.add(sale)
            db.flush()
            subtotal = 0.0
            costo_total = 0.0
            for product in chosen:
                qty = 1 if product.unidad_medida == "Unidad" else round(rng.uniform(0.8, 2.4), 2)
                line = round_money(product.precio_venta * qty)
                cost_line = round_money(product.costo * qty)
                subtotal += line
                costo_total += cost_line
                db.add(
                    SaleItem(
                        sale_id=sale.id,
                        product_id=product.id,
                        cantidad=qty,
                        precio_unitario=product.precio_venta,
                        costo_unitario=product.costo,
                        subtotal=line,
                    )
                )
            sale.subtotal = subtotal
            sale.total = subtotal
            sale.costo_total = costo_total
            sale.ganancia = round_money(subtotal - costo_total)
            db.add(sale)

        if rng.random() < 0.55:
            cats = ["Luz", "Gas", "Alquiler", "Sueldos", "Combustible", "Mantenimiento", "Impuestos"]
            cat = rng.choice(cats)
            amounts = {
                "Luz": 45000,
                "Gas": 28000,
                "Alquiler": 180000,
                "Sueldos": 220000,
                "Combustible": 18000,
                "Mantenimiento": 12000,
                "Impuestos": 35000,
            }
            db.add(
                Expense(
                    categoria=cat,
                    descripcion=f"{cat} de demostración",
                    monto=amounts.get(cat, 10000),
                    fecha=start_of_day(day).replace(hour=8),
                    metodo_pago=rng.choice(["Efectivo", "Transferencia"]),
                    usuario_id=admin.id,
                    observaciones="Dato de demo",
                )
            )

    db.add(
        InventoryMovement(
            product_id=products[0].id,
            tipo="ajuste",
            cantidad=0,
            motivo="Stock inicial de demostración",
            usuario_id=admin.id,
            fecha=now_ar(),
            referencia="seed",
        )
    )
    db.commit()
