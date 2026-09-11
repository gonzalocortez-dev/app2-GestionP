"""Productos, inventario y vendedores."""

from __future__ import annotations

import reflex as rx
from sqlmodel import func, select

from polleria.auth.state import AuthState
from polleria.constants import (
    BRANCHES,
    CHICKEN_BOX_COUNTS,
    CHICKEN_BOX_CUTS,
    INVENTORY_TYPE_LABELS,
    PRODUCT_CATEGORIES,
    ROLE_LABELS,
    UNITS,
)
from polleria.models import InventoryMovement, Product, Sale, User
from polleria.schemas import BoxPreviewRow, MovementRow, ProductRow, UserRow
from polleria.services.core import BusinessError, PermissionDenied, safe_commit
from polleria.services.deletes import delete_product
from polleria.services.ops import ensure_chicken_cut_products, move_inventory, receive_chicken_boxes
from polleria.services.stock import ensure_product_branches, get_or_create_branch_stock, stocks_by_product, sync_product_total
from polleria.states.pos import _product_row
from polleria.utils.forms import form_field
from polleria.utils.money import money, parse_amount
from polleria.utils.time import format_dt, period_range


class ProductState(AuthState):
    items: list[ProductRow] = []
    search: str = ""
    dialog_open: bool = False
    editing_id: int = 0
    form_key: int = 0
    form_nombre: str = ""
    form_descripcion: str = ""
    form_categoria: str = "Pollo"
    form_unidad: str = "Kg"
    form_precio: str = ""
    form_costo: str = ""
    form_stock: str = "0"
    form_minimo: str = "0"
    form_activo: bool = True

    @rx.var(cache=True)
    def filtered(self) -> list[ProductRow]:
        q = self.search.strip().lower()
        if not q:
            return self.items
        return [
            p
            for p in self.items
            if q in p.nombre.lower() or q in p.categoria.lower()
        ]

    @rx.event
    def on_load(self):
        if redir := self._redirect_guest():
            return redir
        if not self._has("products.view"):
            return self._home_redirect()
        self.reload()

    @rx.event
    def reload(self):
        with rx.session() as db:
            rows = db.exec(select(Product).order_by(Product.nombre)).all()
        self.items = [_product_row(p) for p in rows]

    @rx.event
    def open_new(self):
        if not self._has("products.manage"):
            return rx.toast.error("No tenés permisos para gestionar productos.")
        self.editing_id = 0
        self.form_nombre = ""
        self.form_descripcion = ""
        self.form_categoria = PRODUCT_CATEGORIES[0]
        self.form_unidad = UNITS[1]
        self.form_precio = ""
        self.form_costo = ""
        self.form_stock = "0"
        self.form_minimo = "0"
        self.form_activo = True
        self.form_key += 1
        self.dialog_open = True

    @rx.event
    def open_edit(self, product_id: int):
        if not self._has("products.manage"):
            return rx.toast.error("No tenés permisos para gestionar productos.")
        row = next((p for p in self.items if p.id == product_id), None)
        if row is None:
            return
        self.editing_id = row.id
        self.form_nombre = row.nombre
        self.form_descripcion = row.descripcion
        self.form_categoria = row.categoria
        self.form_unidad = row.unidad_medida
        self.form_precio = str(row.precio_venta)
        self.form_costo = str(row.costo)
        self.form_stock = str(row.stock)
        self.form_minimo = str(row.stock_minimo)
        self.form_activo = row.activo
        self.form_key += 1
        self.dialog_open = True

    @rx.event
    def close_dialog(self):
        self.dialog_open = False

    @rx.event
    def set_dialog_open(self, value: bool):
        self.dialog_open = value

    @rx.event
    def save(self, form_data: dict):
        try:
            self._require("products.manage")
            nombre = (form_data.get("nombre") or self.form_nombre or "").strip()
            if not nombre:
                raise BusinessError("El nombre es obligatorio.")
            descripcion = (
                form_data.get("descripcion") or self.form_descripcion or ""
            ).strip()
            categoria = form_field(form_data, "categoria", self.form_categoria)
            unidad = form_field(form_data, "unidad_medida", self.form_unidad)
            precio = parse_amount(form_data.get("precio") or self.form_precio)
            costo = parse_amount(form_data.get("costo") or self.form_costo)
            stock = parse_amount(form_data.get("stock") or self.form_stock)
            minimo = parse_amount(form_data.get("minimo") or self.form_minimo)
            if precio < 0 or costo < 0:
                raise BusinessError("Precio y costo no pueden ser negativos.")
            with rx.session() as db:
                if self.editing_id:
                    product = db.get(Product, self.editing_id)
                    if product is None:
                        raise BusinessError("Producto no encontrado.")
                else:
                    product = Product()
                product.nombre = nombre
                product.descripcion = descripcion
                product.categoria = categoria
                product.unidad_medida = unidad
                product.precio_venta = precio
                product.costo = costo
                product.stock_minimo = minimo
                product.activo = self.form_activo
                db.add(product)
                db.flush()
                ensure_product_branches(db, product.id or 0)
                if not self.editing_id and stock > 0:
                    row = get_or_create_branch_stock(db, product.id or 0, BRANCHES[0])
                    row.cantidad = stock
                    db.add(row)
                sync_product_total(db, product)
                safe_commit(db)
        except (BusinessError, PermissionDenied) as exc:
            return rx.toast.error(str(exc))
        self.dialog_open = False
        self.reload()
        return rx.toast.success("Producto guardado")

    @rx.event
    def toggle_active(self, product_id: int):
        try:
            self._require("products.manage")
            with rx.session() as db:
                product = db.get(Product, product_id)
                if product is None:
                    raise BusinessError("Producto no encontrado.")
                product.activo = not product.activo
                db.add(product)
                safe_commit(db)
        except (BusinessError, PermissionDenied) as exc:
            return rx.toast.error(str(exc))
        self.reload()

    @rx.event
    def delete_item(self, product_id: int):
        try:
            with rx.session() as db:
                result = delete_product(
                    db,
                    actor_id=self.authenticated_user.id,
                    actor_role=self.authenticated_user.role,
                    product_id=product_id,
                )
        except (BusinessError, PermissionDenied) as exc:
            return rx.toast.error(str(exc))
        self.reload()
        if result == "desactivado":
            return rx.toast.success("Producto desactivado: tiene ventas o compras.")
        return rx.toast.success("Producto eliminado")


def _kg_fmt(value: float) -> str:
    return f"{value:.3f}".replace(".", ",") + " kg"


class InventoryState(AuthState):
    items: list[ProductRow] = []
    movements: list[MovementRow] = []
    dialog_open: bool = False
    product_label: str = ""
    product_options: list[str] = []
    tipo: str = "ajuste"
    cantidad: str = ""
    motivo: str = ""
    box_count: str = "1"
    box_sucursal: str = ""
    move_sucursal: str = ""
    box_options: list[str] = list(CHICKEN_BOX_COUNTS)

    @rx.event
    def on_load(self):
        if redir := self._redirect_guest():
            return redir
        if not self._has("inventory.view"):
            return self._home_redirect()
        self.reload()

    @rx.var(cache=True)
    def box_preview(self) -> list[BoxPreviewRow]:
        try:
            boxes = int(self.box_count)
        except ValueError:
            boxes = 1
        rows = []
        for nombre, kg in CHICKEN_BOX_CUTS:
            rows.append(
                BoxPreviewRow(
                    producto=nombre,
                    por_caja_fmt=_kg_fmt(kg),
                    total_fmt=_kg_fmt(round(kg * boxes, 3)),
                )
            )
        return rows

    @rx.event
    def set_box_count(self, value: str):
        self.box_count = value

    @rx.event
    def set_box_sucursal(self, value: str):
        self.box_sucursal = "" if value in {"", "Seleccioná sucursal"} else value

    @rx.event
    def set_move_sucursal(self, value: str):
        self.move_sucursal = "" if value in {"", "Seleccioná sucursal"} else value

    @rx.event
    def receive_boxes(self):
        if not self._has("inventory.manage"):
            return rx.toast.error("No tenés permisos para cargar stock.")
        if not self.box_sucursal.strip() or self.box_sucursal not in BRANCHES:
            return rx.toast.error("Seleccioná en qué sucursal estás cargando las cajas.")
        try:
            boxes = int(self.box_count)
            with rx.session() as db:
                receive_chicken_boxes(
                    db,
                    actor_id=self.authenticated_user.id,
                    actor_role=self.authenticated_user.role,
                    boxes=boxes,
                    sucursal=self.box_sucursal,
                )
        except (ValueError, BusinessError, PermissionDenied) as exc:
            return rx.toast.error(
                str(exc) if not isinstance(exc, ValueError) else "Seleccioná cuántas cajas."
            )
        self.reload()
        return rx.toast.success(
            f"Se cargó el stock de {self.box_count} caja(s) en {self.box_sucursal}."
        )

    @rx.event
    def reload(self):
        with rx.session() as db:
            ensure_chicken_cut_products(db)
            products = db.exec(select(Product).order_by(Product.nombre)).all()
            by_product = stocks_by_product(db, [p.id or 0 for p in products])
            moves = db.exec(
                select(InventoryMovement, Product, User)
                .join(Product, Product.id == InventoryMovement.product_id)
                .join(User, User.id == InventoryMovement.usuario_id)
                .order_by(InventoryMovement.fecha.desc())
                .limit(80)
            ).all()
        self.items = [
            _product_row(
                p,
                qty=sum(by_product.get(p.id or 0, {}).values()),
                by_branch=by_product.get(p.id or 0),
            )
            for p in products
        ]
        self.product_options = [f"{p.id} · {p.nombre}" for p in products]
        self.movements = [
            MovementRow(
                id=m.id or 0,
                fecha=format_dt(m.fecha),
                producto=p.nombre,
                tipo=INVENTORY_TYPE_LABELS.get(m.tipo, m.tipo),
                cantidad_fmt=str(m.cantidad).replace(".", ","),
                motivo=m.motivo,
                sucursal=m.sucursal or "—",
                usuario=u.nombre_completo,
            )
            for m, p, u in moves
        ]

    @rx.event
    def open_move(self):
        if not self._has("inventory.manage"):
            return rx.toast.error("No tenés permisos para ajustar inventario.")
        if self.product_options and not self.product_label:
            self.product_label = self.product_options[0]
        self.tipo = "ajuste"
        self.cantidad = ""
        self.motivo = ""
        self.move_sucursal = self.box_sucursal or BRANCHES[0]
        self.dialog_open = True

    @rx.event
    def close_dialog(self):
        self.dialog_open = False

    @rx.event
    def set_dialog_open(self, value: bool):
        self.dialog_open = value

    @rx.event
    def save_move(self):
        try:
            if not self.move_sucursal.strip() or self.move_sucursal not in BRANCHES:
                return rx.toast.error("Seleccioná la sucursal del movimiento.")
            product_id = int(self.product_label.split(" · ", 1)[0])
            qty = parse_amount(self.cantidad)
            with rx.session() as db:
                move_inventory(
                    db,
                    actor_id=self.authenticated_user.id,
                    actor_role=self.authenticated_user.role,
                    product_id=product_id,
                    tipo=self.tipo,
                    cantidad=qty,
                    motivo=self.motivo.strip() or "Movimiento manual",
                    sucursal=self.move_sucursal,
                )
        except (ValueError, BusinessError, PermissionDenied) as exc:
            return rx.toast.error(str(exc) if not isinstance(exc, ValueError) else "Datos inválidos.")
        self.dialog_open = False
        self.reload()
        return rx.toast.success("Movimiento registrado")


class SellerState(AuthState):
    items: list[UserRow] = []
    dialog_open: bool = False
    editing_id: int = 0
    form_nombre: str = ""
    form_apellido: str = ""
    form_email: str = ""
    form_password: str = ""
    form_activo: bool = True

    @rx.event
    def on_load(self):
        if redir := self._redirect_guest():
            return redir
        if not self._has("sellers.view"):
            return self._home_redirect()
        self.reload()

    @rx.event
    def reload(self):
        start_day, end_day = period_range("hoy")
        start_month, end_month = period_range("mes")
        with rx.session() as db:
            users = db.exec(
                select(User)
                .where(User.role.in_(["vendedor", "supervisor", "admin"]))  # type: ignore[attr-defined]
                .order_by(User.nombre)
            ).all()
            rows = []
            for user in users:
                day_total = db.exec(
                    select(func.coalesce(func.sum(Sale.total), 0)).where(
                        Sale.vendedor_id == user.id,
                        Sale.fecha >= start_day,
                        Sale.fecha < end_day,
                        Sale.estado == "completada",
                    )
                ).one()
                month_total = db.exec(
                    select(func.coalesce(func.sum(Sale.total), 0)).where(
                        Sale.vendedor_id == user.id,
                        Sale.fecha >= start_month,
                        Sale.fecha < end_month,
                        Sale.estado == "completada",
                    )
                ).one()
                rows.append(
                    UserRow(
                        id=user.id or 0,
                        nombre=user.nombre_completo,
                        email=user.email,
                        role=user.role,
                        role_label=ROLE_LABELS.get(user.role, user.role),
                        activo=user.activo,
                        last_activity=format_dt(user.last_activity) if user.last_activity else "—",
                        ventas_dia_fmt=money(float(day_total or 0)),
                        ventas_mes_fmt=money(float(month_total or 0)),
                    )
                )
        self.items = rows

    @rx.event
    def open_new(self):
        if not self._has("sellers.manage"):
            return rx.toast.error("Solo un administrador puede crear vendedores.")
        self.editing_id = 0
        self.form_nombre = ""
        self.form_apellido = ""
        self.form_email = ""
        self.form_password = ""
        self.form_activo = True
        self.dialog_open = True

    @rx.event
    def open_edit(self, user_id: int):
        if not self._has("sellers.manage"):
            return rx.toast.error("Solo un administrador puede editar vendedores.")
        row = next((u for u in self.items if u.id == user_id), None)
        if not row:
            return
        self.editing_id = row.id
        parts = row.nombre.split(" ", 1)
        self.form_nombre = parts[0]
        self.form_apellido = parts[1] if len(parts) > 1 else ""
        self.form_email = row.email
        self.form_password = ""
        self.form_activo = row.activo
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
            self._require("sellers.manage")
            if not self.form_nombre.strip() or not self.form_email.strip():
                raise BusinessError("Nombre y email son obligatorios.")
            email = self.form_email.strip().lower()
            with rx.session() as db:
                if self.editing_id:
                    user = db.get(User, self.editing_id)
                    if user is None:
                        raise BusinessError("Vendedor no encontrado.")
                else:
                    if not self.form_password or len(self.form_password) < 8:
                        raise BusinessError("La contraseña debe tener al menos 8 caracteres.")
                    if db.exec(select(User).where(User.email == email)).first():
                        raise BusinessError("Ese email ya está en uso.")
                    user = User(password_hash=User.hash_password(self.form_password), role="vendedor")
                user.nombre = self.form_nombre.strip()
                user.apellido = self.form_apellido.strip()
                user.email = email
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
        return rx.toast.success("Vendedor guardado")

    @rx.event
    def toggle_active(self, user_id: int):
        try:
            self._require("sellers.manage")
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
