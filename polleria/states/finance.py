"""Gastos, compras y cierre de caja."""

from __future__ import annotations

import reflex as rx
from sqlmodel import select

from polleria.auth.state import AuthState
from polleria.constants import BRANCHES, EXPENSE_CATEGORIES
from polleria.models import CashRegisterClosure, Expense, Product, Purchase, User
from polleria.schemas import ClosureRow, ExpenseRow, ProductRow, PurchaseRow
from polleria.services.core import BusinessError, PermissionDenied, audit, safe_commit
from polleria.services.deletes import delete_expense, delete_purchase
from polleria.services.ops import create_purchase, register_expense
from polleria.services import queries
from polleria.states.pos import _product_row
from polleria.utils.money import money, parse_amount, round_money
from polleria.utils.time import format_dt, iso_date, now_ar, parse_date, period_range, start_of_day


from polleria.utils.forms import form_field


class ExpenseState(AuthState):
    items: list[ExpenseRow] = []
    dialog_open: bool = False
    form_key: int = 0
    categoria: str = EXPENSE_CATEGORIES[0]
    descripcion: str = ""
    monto: str = ""
    fecha: str = ""
    metodo_pago: str = "Efectivo"
    sucursal: str = ""
    observaciones: str = ""

    @rx.event
    def on_load(self):
        if redir := self._redirect_guest():
            return redir
        if not self._has("expenses.manage"):
            return self._home_redirect()
        self.fecha = iso_date()
        self.reload()

    @rx.event
    def reload(self):
        with rx.session() as db:
            rows = db.exec(select(Expense).order_by(Expense.fecha.desc()).limit(200)).all()
        self.items = [
            ExpenseRow(
                id=e.id or 0,
                fecha=format_dt(e.fecha),
                categoria=e.categoria,
                descripcion=e.descripcion,
                sucursal=e.sucursal or "—",
                importe_fmt=money(e.monto),
            )
            for e in rows
        ]

    @rx.event
    def open_new(self):
        self.categoria = EXPENSE_CATEGORIES[0]
        self.descripcion = ""
        self.monto = ""
        self.fecha = iso_date()
        self.metodo_pago = "Efectivo"
        self.sucursal = BRANCHES[0]
        self.observaciones = ""
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
        categoria = form_field(form_data, "categoria", self.categoria)
        descripcion = form_field(form_data, "descripcion", self.descripcion)
        monto = parse_amount(form_field(form_data, "monto", self.monto))
        fecha_raw = form_field(form_data, "fecha", self.fecha or iso_date())
        metodo_pago = form_field(form_data, "metodo_pago", self.metodo_pago or "Efectivo")
        sucursal = form_field(form_data, "sucursal", self.sucursal)
        observaciones = form_field(form_data, "observaciones", self.observaciones)
        if not categoria:
            return rx.toast.error("Elegí una categoría.")
        if not sucursal.strip() or sucursal.strip() not in BRANCHES:
            return rx.toast.error("Seleccioná la sucursal.")
        if monto <= 0:
            return rx.toast.error("El importe debe ser mayor a cero.")
        if self.authenticated_user.id < 0:
            return rx.toast.error("Sesión expirada. Volvé a iniciar sesión.")
        try:
            with rx.session() as db:
                register_expense(
                    db,
                    actor_id=self.authenticated_user.id,
                    actor_role=self.authenticated_user.role,
                    categoria=categoria,
                    descripcion=descripcion,
                    monto=monto,
                    fecha=start_of_day(parse_date(fecha_raw)),
                    metodo_pago=metodo_pago,
                    sucursal=sucursal,
                    observaciones=observaciones,
                )
        except (BusinessError, PermissionDenied) as exc:
            return rx.toast.error(str(exc))
        except Exception as exc:
            return rx.toast.error(f"No se pudo guardar el gasto: {exc}")
        self.dialog_open = False
        self.reload()
        return rx.toast.success("Gasto registrado")

    @rx.event
    def delete_item(self, expense_id: int):
        try:
            with rx.session() as db:
                delete_expense(
                    db,
                    actor_id=self.authenticated_user.id,
                    actor_role=self.authenticated_user.role,
                    expense_id=expense_id,
                )
        except (BusinessError, PermissionDenied) as exc:
            return rx.toast.error(str(exc))
        self.reload()
        return rx.toast.success("Gasto eliminado")


class PurchaseState(AuthState):
    items: list[PurchaseRow] = []
    products: list[ProductRow] = []
    dialog_open: bool = False
    form_key: int = 0
    line_form_key: int = 0
    proveedor: str = ""
    fecha: str = ""
    sucursal: str = ""
    observaciones: str = ""
    registrar_gasto: bool = True
    metodo_pago: str = "Efectivo"
    product_label: str = ""
    product_options: list[str] = []
    qty: str = "1"
    costo: str = ""
    line_nombre: str = ""
    line_qty: str = ""
    line_costo: str = ""
    line_subtotal: str = ""
    # Simple single-product-at-a-time draft stored as CSV-like rows in lists
    draft_names: list[str] = []
    draft_qtys: list[str] = []
    draft_costos: list[str] = []
    draft_ids: list[int] = []

    @rx.var(cache=True)
    def draft_total_fmt(self) -> str:
        total = 0.0
        for qty, costo in zip(self.draft_qtys, self.draft_costos):
            total += parse_amount(qty) * parse_amount(costo)
        return money(total)

    @rx.event
    def on_load(self):
        if redir := self._redirect_guest():
            return redir
        if not self._has("purchases.view"):
            return self._home_redirect()
        self.fecha = iso_date()
        self.reload()

    @rx.event
    def reload(self):
        with rx.session() as db:
            purchases = db.exec(select(Purchase, User).join(User, User.id == Purchase.usuario_id).order_by(Purchase.fecha.desc()).limit(100)).all()
            products = db.exec(select(Product).where(Product.activo == True).order_by(Product.nombre)).all()  # noqa: E712
        self.items = [
            PurchaseRow(
                id=p.id or 0,
                fecha=format_dt(p.fecha),
                proveedor=p.proveedor,
                sucursal=p.sucursal or "—",
                total_fmt=money(p.total),
                usuario=u.nombre_completo,
            )
            for p, u in purchases
        ]
        self.products = [_product_row(p) for p in products]
        self.product_options = [f"{p.id} · {p.nombre}" for p in products]
        if self.product_options and not self.product_label:
            self.product_label = self.product_options[0]

    @rx.event
    def open_new(self):
        if not self._has("purchases.manage"):
            return rx.toast.error("Solo un administrador puede registrar compras.")
        self.proveedor = ""
        self.fecha = iso_date()
        self.sucursal = BRANCHES[0]
        self.observaciones = ""
        self.registrar_gasto = True
        self.qty = "1"
        self.costo = ""
        self.draft_names = []
        self.draft_qtys = []
        self.draft_costos = []
        self.draft_ids = []
        if self.product_options:
            self.product_label = self.product_options[0]
        self.line_form_key += 1
        self.form_key += 1
        self.dialog_open = True

    @rx.event
    def close_dialog(self):
        self.dialog_open = False

    @rx.event
    def set_dialog_open(self, value: bool):
        self.dialog_open = value

    @rx.event
    def set_proveedor(self, value: str):
        self.proveedor = value

    @rx.event
    def set_fecha(self, value: str):
        self.fecha = value

    @rx.event
    def set_sucursal(self, value: str):
        self.sucursal = "" if value in {"", "Seleccioná sucursal"} else value

    @rx.event
    def set_product_label(self, value: str):
        self.product_label = value

    @rx.event
    def set_qty(self, value: str):
        self.qty = value

    @rx.event
    def set_costo(self, value: str):
        self.costo = value

    @rx.event
    def set_registrar_gasto(self, value: bool):
        self.registrar_gasto = value

    @rx.event
    def set_metodo_pago(self, value: str):
        self.metodo_pago = value

    @rx.event
    def add_line(self, form_data: dict):
        product_label = self.product_label.strip()
        if not product_label:
            return rx.toast.error("Seleccioná un producto.")
        try:
            product_id = int(product_label.split(" · ", 1)[0])
            nombre = product_label.split(" · ", 1)[1]
        except (ValueError, IndexError):
            return rx.toast.error("Seleccioná un producto válido.")
        qty = parse_amount(form_field(form_data, "qty", self.qty or "1"))
        costo = parse_amount(form_field(form_data, "costo", self.costo))
        if qty <= 0:
            return rx.toast.error("La cantidad debe ser mayor a cero.")
        if costo <= 0:
            return rx.toast.error("Ingresá el costo unitario.")
        self.draft_ids = self.draft_ids + [product_id]
        self.draft_names = self.draft_names + [nombre]
        self.draft_qtys = self.draft_qtys + [str(qty)]
        self.draft_costos = self.draft_costos + [str(costo)]
        self.qty = "1"
        self.costo = ""
        self.line_form_key += 1
        return rx.toast.success(f"Agregado: {nombre}")

    @rx.event
    def save(self):
        if not self.proveedor.strip():
            return rx.toast.error("Ingresá el proveedor.")
        if not self.sucursal.strip() or self.sucursal not in BRANCHES:
            return rx.toast.error("Seleccioná la sucursal de la compra.")
        items = [
            {
                "product_id": pid,
                "cantidad": parse_amount(qty),
                "costo_unitario": parse_amount(costo),
            }
            for pid, qty, costo in zip(self.draft_ids, self.draft_qtys, self.draft_costos)
        ]
        if not items:
            return rx.toast.error("Agregá al menos un producto a la compra.")
        try:
            with rx.session() as db:
                create_purchase(
                    db,
                    actor_id=self.authenticated_user.id,
                    actor_role=self.authenticated_user.role,
                    proveedor=self.proveedor,
                    items=items,
                    fecha=start_of_day(parse_date(self.fecha)),
                    registrar_gasto=self.registrar_gasto,
                    observaciones=self.observaciones,
                    metodo_pago=self.metodo_pago,
                    sucursal=self.sucursal,
                )
        except (BusinessError, PermissionDenied) as exc:
            return rx.toast.error(str(exc))
        except Exception as exc:
            return rx.toast.error(f"No se pudo registrar la compra: {exc}")
        self.dialog_open = False
        self.reload()
        return rx.toast.success("Compra registrada e inventario actualizado")

    @rx.event
    def delete_item(self, purchase_id: int):
        try:
            with rx.session() as db:
                delete_purchase(
                    db,
                    actor_id=self.authenticated_user.id,
                    actor_role=self.authenticated_user.role,
                    purchase_id=purchase_id,
                )
        except (BusinessError, PermissionDenied) as exc:
            return rx.toast.error(str(exc))
        self.reload()
        return rx.toast.success("Compra eliminada")


class CashState(AuthState):
    efectivo_fmt: str = "$0,00"
    transferencias_fmt: str = "$0,00"
    tarjetas_fmt: str = "$0,00"
    gastos_fmt: str = "$0,00"
    total_fmt: str = "$0,00"
    operaciones: int = 0
    efectivo_esperado: float = 0.0
    efectivo_contado: str = ""
    observaciones: str = ""
    diferencia_fmt: str = "$0,00"
    history: list[ClosureRow] = []

    @rx.var(cache=True)
    def diferencia(self) -> float:
        return round_money(parse_amount(self.efectivo_contado) - self.efectivo_esperado)

    @rx.var(cache=True)
    def diferencia_live_fmt(self) -> str:
        return money(self.diferencia)

    @rx.event
    def on_load(self):
        if redir := self._redirect_guest():
            return redir
        if not self._has("cash.close"):
            return self._home_redirect()
        self.reload()

    @rx.event
    def reload(self):
        start, end = period_range("hoy")
        own = self.is_vendedor
        vid = self.authenticated_user.id if own else None
        with rx.session() as db:
            totals = queries.cash_totals(db, start, end, vendedor_id=vid)
            rows = db.exec(
                select(CashRegisterClosure, User)
                .join(User, User.id == CashRegisterClosure.usuario_id)
                .order_by(CashRegisterClosure.fecha.desc())
                .limit(30)
            ).all()
        self.efectivo_fmt = totals["efectivo_fmt"]
        self.transferencias_fmt = totals["transferencias_fmt"]
        self.tarjetas_fmt = totals["tarjetas_fmt"]
        self.gastos_fmt = totals["gastos_fmt"]
        self.total_fmt = totals["total_fmt"]
        self.operaciones = totals["operaciones"]
        self.efectivo_esperado = totals["efectivo"]
        self.diferencia_fmt = money(self.diferencia)
        self.history = [
            ClosureRow(
                id=c.id or 0,
                fecha=format_dt(c.fecha),
                efectivo_fmt=money(c.efectivo_esperado),
                transferencias_fmt=money(c.total_transferencias),
                tarjetas_fmt=money(c.total_tarjetas),
                gastos_fmt=money(getattr(c, "total_gastos", 0) or 0),
                total_fmt=money(
                    c.ganancia_neta
                    if (c.total_gastos or c.ganancia_neta)
                    else c.total_ventas
                ),
            )
            for c, u in rows
        ]

    @rx.event
    def close_register(self):
        counted = parse_amount(self.efectivo_contado)
        diff = round_money(counted - self.efectivo_esperado)
        try:
            self._require("cash.close")
            with rx.session() as db:
                start, end = period_range("hoy")
                vid = self.authenticated_user.id if self.is_vendedor else None
                totals = queries.cash_totals(db, start, end, vendedor_id=vid)
                closure = CashRegisterClosure(
                    usuario_id=self.authenticated_user.id,
                    fecha=now_ar(),
                    efectivo_esperado=totals["efectivo"],
                    efectivo_contado=counted,
                    diferencia=round_money(counted - totals["efectivo"]),
                    total_ventas=totals.get("ventas", totals["total"]),
                    total_transferencias=totals["transferencias"],
                    total_tarjetas=totals["tarjetas"],
                    total_mercadopago=0,
                    total_gastos=totals["gastos"],
                    ganancia_neta=totals["ganancia_neta"],
                    cantidad_operaciones=totals["operaciones"],
                    observaciones=self.observaciones,
                )
                db.add(closure)
                db.flush()
                audit(
                    db,
                    usuario_id=self.authenticated_user.id,
                    accion="cash.close",
                    entidad="cash_register_closure",
                    entidad_id=closure.id,
                    detalle=f"dif={diff}",
                )
                safe_commit(db)
        except PermissionDenied as exc:
            return rx.toast.error(str(exc))
        self.observaciones = ""
        self.reload()
        return rx.toast.success("Cierre de caja guardado")
