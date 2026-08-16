"""Punto de venta: carrito, cobro y venta rápida."""

from __future__ import annotations

from datetime import datetime

import reflex as rx
from sqlmodel import select

from polleria.auth.state import AuthState
from polleria.constants import PAYMENT_METHODS
from polleria.models import Product, User
from polleria.schemas import CartItem, ProductRow
from polleria.services.core import BusinessError, DatabaseUnavailable, PermissionDenied
from polleria.services.sales import create_detailed_sale, create_quick_sale
from polleria.utils.money import money, parse_amount, round_money
from polleria.utils.time import iso_date, now_ar, parse_date, start_of_day


def _product_row(p: Product) -> ProductRow:
    estado = p.stock_estado
    labels = {
        "stock_normal": "Stock normal",
        "stock_bajo": "Stock bajo",
        "sin_stock": "Sin stock",
    }
    return ProductRow(
        id=p.id or 0,
        nombre=p.nombre,
        descripcion=p.descripcion,
        categoria=p.categoria,
        unidad_medida=p.unidad_medida,
        precio_venta=p.precio_venta,
        precio_fmt=money(p.precio_venta),
        costo=p.costo,
        costo_fmt=money(p.costo),
        stock=p.stock,
        stock_fmt=str(p.stock).replace(".", ","),
        stock_minimo=p.stock_minimo,
        valor_fmt=money(p.valor_inventario),
        estado=estado,
        estado_label=labels[estado],
        activo=p.activo,
    )


class POSState(AuthState):
    mode: str = "detallada"
    search: str = ""
    qty_input: str = "1"
    discount_input: str = "0"
    metodo_pago: str = "Efectivo"
    observacion: str = ""
    quick_amount: str = ""
    sale_date: str = ""

    seller_label: str = ""
    seller_id: int = 0
    seller_options: list[str] = []
    seller_locked: bool = False

    products: list[ProductRow] = []
    cart: list[CartItem] = []

    show_confirm: bool = False
    last_numero: str = ""
    last_total: str = ""
    last_vendedor: str = ""
    last_pago: str = ""
    last_fecha: str = ""

    @rx.var(cache=True)
    def is_quick(self) -> bool:
        return self.mode == "rapida"

    @rx.var(cache=True)
    def filtered_products(self) -> list[ProductRow]:
        q = self.search.strip().lower()
        items = [p for p in self.products if p.activo]
        if not q:
            return items
        return [
            p
            for p in items
            if q in p.nombre.lower() or q in p.categoria.lower()
        ]

    @rx.var(cache=True)
    def subtotal(self) -> float:
        return round_money(sum(i.subtotal for i in self.cart))

    @rx.var(cache=True)
    def descuento(self) -> float:
        value = parse_amount(self.discount_input)
        return min(value, self.subtotal)

    @rx.var(cache=True)
    def total(self) -> float:
        return round_money(self.subtotal - self.descuento)

    @rx.var(cache=True)
    def subtotal_fmt(self) -> str:
        return money(self.subtotal)

    @rx.var(cache=True)
    def descuento_fmt(self) -> str:
        return money(self.descuento)

    @rx.var(cache=True)
    def total_fmt(self) -> str:
        return money(self.total)

    @rx.var(cache=True)
    def cart_count(self) -> int:
        return len(self.cart)

    @rx.event
    def on_load(self):
        self._bootstrap()
        if not self.is_authenticated:
            return rx.redirect("/login")
        if not self._has("pos"):
            return rx.redirect("/")
        self.sale_date = iso_date()
        self._load_sellers()
        self._load_products()

    def _load_sellers(self) -> None:
        with rx.session() as db:
            users = db.exec(
                select(User).where(User.activo == True).order_by(User.nombre)  # noqa: E712
            ).all()
        self.seller_options = [
            f"{u.id} · {u.nombre_completo}" for u in users if u.role in {"admin", "supervisor", "vendedor"}
        ]
        me = self.authenticated_user
        if me.role == "vendedor":
            self.seller_id = me.id
            self.seller_label = f"{me.id} · {me.nombre_completo}"
            self.seller_locked = True
        elif not self.seller_label and self.seller_options:
            if me.id >= 0:
                match = next((o for o in self.seller_options if o.startswith(f"{me.id} ·")), None)
                self.seller_label = match or self.seller_options[0]
                self.seller_id = int(self.seller_label.split(" · ", 1)[0])
            else:
                self.seller_label = self.seller_options[0]
                self.seller_id = int(self.seller_options[0].split(" · ", 1)[0])
            self.seller_locked = False

    def _load_products(self) -> None:
        with rx.session() as db:
            rows = db.exec(
                select(Product).where(Product.activo == True).order_by(Product.nombre)  # noqa: E712
            ).all()
        self.products = [_product_row(p) for p in rows]

    @rx.event
    def set_mode(self, mode: str):
        self.mode = mode

    @rx.event
    def set_seller_label(self, label: str):
        if self.seller_locked:
            return
        self.seller_label = label
        try:
            self.seller_id = int(label.split(" · ", 1)[0])
        except ValueError:
            self.seller_id = 0

    @rx.event
    def add_product(self, product_id: int):
        qty = parse_amount(self.qty_input)
        if qty <= 0:
            return rx.toast.error("La cantidad debe ser positiva.")
        product = next((p for p in self.products if p.id == product_id), None)
        if product is None:
            return rx.toast.error("Producto no encontrado.")
        existing = [i for i in self.cart if i.product_id == product_id]
        if existing:
            item = existing[0]
            item.cantidad = round_money(item.cantidad + qty)
            item.subtotal = round_money(item.cantidad * item.precio_unitario)
            item.cantidad_fmt = str(item.cantidad).replace(".", ",")
            item.subtotal_fmt = money(item.subtotal)
            self.cart = [item if i.product_id == product_id else i for i in self.cart]
        else:
            subtotal = round_money(product.precio_venta * qty)
            self.cart = self.cart + [
                CartItem(
                    product_id=product.id,
                    nombre=product.nombre,
                    unidad=product.unidad_medida,
                    cantidad=qty,
                    cantidad_fmt=str(qty).replace(".", ","),
                    precio_unitario=product.precio_venta,
                    precio_fmt=product.precio_fmt,
                    costo_unitario=product.costo,
                    subtotal=subtotal,
                    subtotal_fmt=money(subtotal),
                )
            ]
        self.qty_input = "1"
        return rx.toast.success(f"{product.nombre} agregado")

    @rx.event
    def bump_qty(self, product_id: int, delta: float):
        updated: list[CartItem] = []
        for item in self.cart:
            if item.product_id == product_id:
                nueva = round_money(item.cantidad + delta)
                if nueva <= 0:
                    continue
                item.cantidad = nueva
                item.subtotal = round_money(nueva * item.precio_unitario)
                item.cantidad_fmt = str(nueva).replace(".", ",")
                item.subtotal_fmt = money(item.subtotal)
            updated.append(item)
        self.cart = updated

    @rx.event
    def remove_item(self, product_id: int):
        self.cart = [i for i in self.cart if i.product_id != product_id]

    @rx.event
    def clear_cart(self):
        self.cart = []
        self.discount_input = "0"
        self.observacion = ""
        self.quick_amount = ""

    def _sale_when(self) -> datetime:
        d = parse_date(self.sale_date)
        now = now_ar()
        return start_of_day(d).replace(hour=now.hour, minute=now.minute, second=now.second)

    @rx.event
    def confirm_sale(self):
        if self.seller_id <= 0:
            return rx.toast.error("Seleccioná un vendedor.")
        try:
            with rx.session() as db:
                if self.mode == "rapida":
                    importe = parse_amount(self.quick_amount)
                    sale = create_quick_sale(
                        db,
                        actor_id=self.authenticated_user.id,
                        actor_role=self.authenticated_user.role,
                        vendedor_id=self.seller_id,
                        importe=importe,
                        metodo_pago=self.metodo_pago,
                        observacion=self.observacion,
                        fecha=self._sale_when(),
                    )
                else:
                    sale = create_detailed_sale(
                        db,
                        actor_id=self.authenticated_user.id,
                        actor_role=self.authenticated_user.role,
                        vendedor_id=self.seller_id,
                        items=[
                            {
                                "product_id": i.product_id,
                                "cantidad": i.cantidad,
                                "precio_unitario": i.precio_unitario,
                            }
                            for i in self.cart
                        ],
                        metodo_pago=self.metodo_pago,
                        descuento=self.descuento,
                        observacion=self.observacion,
                        fecha=self._sale_when(),
                    )
        except (BusinessError, PermissionDenied, DatabaseUnavailable) as exc:
            return rx.toast.error(str(exc))
        except Exception:
            return rx.toast.error("No se pudo registrar la venta. No se descontó stock.")

        self.last_numero = f"#{sale.id:05d}"
        self.last_total = money(sale.total)
        self.last_vendedor = self.seller_label.split(" · ", 1)[-1]
        self.last_pago = sale.metodo_pago
        self.last_fecha = now_ar().strftime("%d/%m/%Y %H:%M")
        self.show_confirm = True
        self.cart = []
        self.discount_input = "0"
        self.observacion = ""
        self.quick_amount = ""
        self._load_products()
        return rx.toast.success("Venta registrada correctamente")

    @rx.event
    def close_confirm(self):
        self.show_confirm = False
