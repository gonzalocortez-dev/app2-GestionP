"""Páginas de catálogo, finanzas, reportes y administración."""

from __future__ import annotations

import reflex as rx

from polleria.auth.state import AuthState
from polleria.components.layout import app_shell
from polleria.components.widgets import delete_button, empty_state, kpi_card, labeled_input, labeled_native_select, labeled_select, section_card, status_badge, table_wrap
from polleria.constants import BRANCHES, CHICKEN_BOX_COUNTS, EXPENSE_CATEGORIES, INVENTORY_TYPES, PAYMENT_METHODS, PERIODS, PRODUCT_CATEGORIES, ROLE_LABELS, UNITS
from polleria.states.admin import ReportState, SalesListState, SettingsState, UsersAdminState
from polleria.states.catalog import InventoryState, ProductState, SellerState
from polleria.states.finance import CashState, ExpenseState, PurchaseState


def products_page() -> rx.Component:
    return app_shell(
        "Productos",
        rx.cond(
            AuthState.can_manage_products,
            rx.button("Nuevo producto", on_click=ProductState.open_new, size="3"),
            rx.fragment(),
        ),
        rx.input(placeholder="Buscar por nombre o categoría", value=ProductState.search, on_change=ProductState.set_search, size="3", width="100%", max_width="420px"),
        _product_dialog(),
        rx.cond(
            ProductState.filtered.length() > 0,
            table_wrap(
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell("Producto"),
                            rx.table.column_header_cell("Categoría"),
                            rx.table.column_header_cell("Precio"),
                            rx.table.column_header_cell("Costo"),
                            rx.table.column_header_cell("Stock"),
                            rx.table.column_header_cell("Estado"),
                            rx.table.column_header_cell(""),
                        )
                    ),
                    rx.table.body(
                        rx.foreach(
                            ProductState.filtered,
                            lambda p: rx.table.row(
                                rx.table.cell(rx.text(p.nombre, weight="medium")),
                                rx.table.cell(p.categoria),
                                rx.table.cell(p.precio_fmt),
                                rx.table.cell(p.costo_fmt),
                                rx.table.cell(p.stock_fmt + " " + p.unidad_medida),
                                rx.table.cell(status_badge(p.estado)),
                                rx.table.cell(
                                    rx.hstack(
                                        rx.cond(
                                            AuthState.can_manage_products,
                                            rx.button("Editar", size="1", variant="soft", on_click=ProductState.open_edit(p.id)),
                                            rx.fragment(),
                                        ),
                                        delete_button(ProductState.delete_item(p.id)),
                                        spacing="2",
                                    )
                                ),
                            ),
                        )
                    ),
                    width="100%",
                    variant="surface",
                )
            ),
            empty_state("No hay productos", "package"),
        ),
    )


def _product_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title(rx.cond(ProductState.editing_id > 0, "Editar producto", "Nuevo producto")),
            rx.form(
                rx.vstack(
                    labeled_input(
                        "Nombre",
                        name="nombre",
                        default_value=ProductState.form_nombre,
                        required=True,
                    ),
                    labeled_input(
                        "Descripción",
                        name="descripcion",
                        default_value=ProductState.form_descripcion,
                    ),
                    labeled_native_select(
                        "Categoría",
                        list(PRODUCT_CATEGORIES),
                        name="categoria",
                        required=True,
                    ),
                    labeled_native_select(
                        "Unidad",
                        list(UNITS),
                        name="unidad_medida",
                        required=True,
                    ),
                    rx.grid(
                        labeled_input(
                            "Precio de venta",
                            name="precio",
                            default_value=ProductState.form_precio,
                            type="number",
                            step="0.01",
                        ),
                        labeled_input(
                            "Costo",
                            name="costo",
                            default_value=ProductState.form_costo,
                            type="number",
                            step="0.01",
                        ),
                        labeled_input(
                            "Stock inicial",
                            name="stock",
                            default_value=ProductState.form_stock,
                            type="number",
                            step="0.01",
                        ),
                        labeled_input(
                            "Stock mínimo",
                            name="minimo",
                            default_value=ProductState.form_minimo,
                            type="number",
                            step="0.01",
                        ),
                        columns="2",
                        spacing="3",
                        width="100%",
                    ),
                    rx.hstack(
                        rx.switch(
                            checked=ProductState.form_activo,
                            on_change=ProductState.set_form_activo,
                        ),
                        rx.text("Activo"),
                        spacing="2",
                    ),
                    rx.hstack(
                        rx.dialog.close(
                            rx.button(
                                "Cancelar",
                                variant="soft",
                                color_scheme="gray",
                                on_click=ProductState.close_dialog,
                            )
                        ),
                        rx.button("Guardar", type="submit"),
                        justify="end",
                        width="100%",
                    ),
                    spacing="3",
                    width="100%",
                ),
                key=ProductState.form_key,
                on_submit=ProductState.save,
                reset_on_submit=False,
                width="100%",
            ),
            max_width="560px",
        ),
        open=ProductState.dialog_open,
        on_open_change=ProductState.set_dialog_open,
    )


def _chicken_box_card() -> rx.Component:
    return section_card(
        rx.heading("Cargar cajas de pollo (20 kg)", size="5"),
        rx.text(
            "Cada caja suma siempre los mismos kilos. Esos valores no se cambian.",
            color=rx.color("slate", 11),
        ),
        rx.hstack(
            labeled_select(
                "Sucursal",
                ["Seleccioná sucursal", *BRANCHES],
                value=rx.cond(
                    InventoryState.box_sucursal != "",
                    InventoryState.box_sucursal,
                    "Seleccioná sucursal",
                ),
                on_change=InventoryState.set_box_sucursal,
            ),
            labeled_select(
                "Cantidad de cajas",
                list(CHICKEN_BOX_COUNTS),
                value=InventoryState.box_count,
                on_change=InventoryState.set_box_count,
            ),
            rx.button(
                "Cargar stock",
                on_click=InventoryState.receive_boxes,
                size="3",
                height="44px",
                color_scheme="orange",
            ),
            spacing="3",
            align="end",
            wrap="wrap",
            width="100%",
        ),
        table_wrap(
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell("Corte"),
                        rx.table.column_header_cell("Por caja"),
                        rx.table.column_header_cell("Se suma"),
                    )
                ),
                rx.table.body(
                    rx.foreach(
                        InventoryState.box_preview,
                        lambda row: rx.table.row(
                            rx.table.cell(row.producto),
                            rx.table.cell(row.por_caja_fmt),
                            rx.table.cell(rx.text(row.total_fmt, weight="bold")),
                        ),
                    )
                ),
                width="100%",
                variant="surface",
            )
        ),
    )


def inventory_page() -> rx.Component:
    return app_shell(
        "Inventario",
        rx.cond(
            AuthState.can_manage_inventory,
            _chicken_box_card(),
            rx.fragment(),
        ),
        rx.cond(
            AuthState.can_manage_inventory,
            rx.button("Movimiento", on_click=InventoryState.open_move, size="3"),
            rx.fragment(),
        ),
        rx.dialog.root(
            rx.dialog.content(
                rx.dialog.title("Movimiento de inventario"),
                rx.vstack(
                    labeled_select("Producto", InventoryState.product_options, value=InventoryState.product_label, on_change=InventoryState.set_product_label),
                    labeled_select(
                        "Sucursal",
                        ["Seleccioná sucursal", *BRANCHES],
                        value=rx.cond(
                            InventoryState.move_sucursal != "",
                            InventoryState.move_sucursal,
                            "Seleccioná sucursal",
                        ),
                        on_change=InventoryState.set_move_sucursal,
                    ),
                    labeled_select("Tipo", list(INVENTORY_TYPES), value=InventoryState.tipo, on_change=InventoryState.set_tipo),
                    labeled_input("Cantidad (+ entra / − sale en ajuste)", value=InventoryState.cantidad, on_change=InventoryState.set_cantidad),
                    labeled_input("Motivo", value=InventoryState.motivo, on_change=InventoryState.set_motivo),
                    rx.hstack(
                        rx.dialog.close(rx.button("Cancelar", variant="soft", on_click=InventoryState.close_dialog)),
                        rx.button("Confirmar", on_click=InventoryState.save_move),
                        justify="end",
                        width="100%",
                    ),
                    spacing="3",
                    width="100%",
                ),
            ),
            open=InventoryState.dialog_open,
            on_open_change=InventoryState.set_dialog_open,
        ),
        table_wrap(
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell("Producto"),
                        rx.table.column_header_cell(BRANCHES[0]),
                        rx.table.column_header_cell(BRANCHES[1]),
                        rx.table.column_header_cell(BRANCHES[2]),
                        rx.table.column_header_cell("Total"),
                        rx.table.column_header_cell("Mínimo"),
                        rx.table.column_header_cell("Costo"),
                        rx.table.column_header_cell("Precio"),
                        rx.table.column_header_cell("Estado"),
                    )
                ),
                rx.table.body(
                    rx.foreach(
                        InventoryState.items,
                        lambda p: rx.table.row(
                            rx.table.cell(p.nombre),
                            rx.table.cell(p.stock_b1),
                            rx.table.cell(p.stock_b2),
                            rx.table.cell(p.stock_b3),
                            rx.table.cell(p.stock_fmt),
                            rx.table.cell(p.stock_minimo),
                            rx.table.cell(p.costo_fmt),
                            rx.table.cell(p.precio_fmt),
                            rx.table.cell(status_badge(p.estado)),
                        ),
                    )
                ),
                width="100%",
                variant="surface",
            )
        ),
        rx.heading("Historial", size="5"),
        table_wrap(
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell("Fecha"),
                        rx.table.column_header_cell("Producto"),
                        rx.table.column_header_cell("Tipo"),
                        rx.table.column_header_cell("Cantidad"),
                        rx.table.column_header_cell("Sucursal"),
                        rx.table.column_header_cell("Motivo"),
                        rx.table.column_header_cell("Usuario"),
                    )
                ),
                rx.table.body(
                    rx.foreach(
                        InventoryState.movements,
                        lambda m: rx.table.row(
                            rx.table.cell(m.fecha),
                            rx.table.cell(m.producto),
                            rx.table.cell(m.tipo),
                            rx.table.cell(m.cantidad_fmt),
                            rx.table.cell(m.sucursal),
                            rx.table.cell(m.motivo),
                            rx.table.cell(m.usuario),
                        ),
                    )
                ),
                width="100%",
                variant="surface",
            )
        ),
    )


def expenses_page() -> rx.Component:
    return app_shell(
        "Gastos",
        rx.button("Nuevo gasto", on_click=ExpenseState.open_new, size="3"),
        rx.dialog.root(
            rx.dialog.content(
                rx.dialog.title("Registrar gasto"),
                rx.form(
                    rx.vstack(
                        labeled_native_select(
                            "Categoría",
                            list(EXPENSE_CATEGORIES),
                            name="categoria",
                            required=True,
                        ),
                        labeled_input(
                            "Descripción",
                            name="descripcion",
                            default_value=ExpenseState.descripcion,
                            placeholder="Detalle del gasto",
                        ),
                        labeled_input(
                            "Importe",
                            name="monto",
                            default_value=ExpenseState.monto,
                            type="number",
                            step="0.01",
                            min="0.01",
                            placeholder="0.00",
                            required=True,
                        ),
                        labeled_input(
                            "Fecha",
                            name="fecha",
                            type="date",
                            default_value=ExpenseState.fecha,
                        ),
                        labeled_native_select(
                            "Método de pago",
                            list(PAYMENT_METHODS),
                            name="metodo_pago",
                            required=True,
                        ),
                        labeled_native_select(
                            "Sucursal",
                            list(BRANCHES),
                            name="sucursal",
                            required=True,
                        ),
                        labeled_input(
                            "Observaciones",
                            name="observaciones",
                            default_value=ExpenseState.observaciones,
                        ),
                        rx.hstack(
                            rx.dialog.close(
                                rx.button(
                                    "Cancelar",
                                    variant="soft",
                                    on_click=ExpenseState.close_dialog,
                                )
                            ),
                            rx.button("Guardar", type="submit"),
                            justify="end",
                            width="100%",
                        ),
                        spacing="3",
                        width="100%",
                    ),
                    key=ExpenseState.form_key,
                    on_submit=ExpenseState.save,
                    reset_on_submit=False,
                    width="100%",
                ),
            ),
            open=ExpenseState.dialog_open,
            on_open_change=ExpenseState.set_dialog_open,
        ),
        table_wrap(
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell("Fecha"),
                        rx.table.column_header_cell("Categoría"),
                        rx.table.column_header_cell("Descripción"),
                        rx.table.column_header_cell("Sucursal"),
                        rx.table.column_header_cell("Importe"),
                        rx.table.column_header_cell(""),
                    )
                ),
                rx.table.body(
                    rx.foreach(
                        ExpenseState.items,
                        lambda e: rx.table.row(
                            rx.table.cell(e.fecha),
                            rx.table.cell(e.categoria),
                            rx.table.cell(e.descripcion),
                            rx.table.cell(e.sucursal),
                            rx.table.cell(e.importe_fmt),
                            rx.table.cell(delete_button(ExpenseState.delete_item(e.id))),
                        ),
                    )
                ),
                width="100%",
                variant="surface",
            )
        ),
    )


def purchases_page() -> rx.Component:
    return app_shell(
        "Compras",
        rx.cond(
            AuthState.can_manage_purchases,
            rx.button("Nueva compra", on_click=PurchaseState.open_new, size="3"),
            rx.fragment(),
        ),
        rx.dialog.root(
            rx.dialog.content(
                rx.dialog.title("Registrar compra"),
                rx.box(
                    rx.vstack(
                        labeled_input(
                            "Proveedor",
                            default_value=PurchaseState.proveedor,
                            on_change=PurchaseState.set_proveedor,
                            required=True,
                        ),
                        labeled_input(
                            "Fecha",
                            type="date",
                            default_value=PurchaseState.fecha,
                            on_change=PurchaseState.set_fecha,
                            required=True,
                        ),
                        labeled_select(
                            "Sucursal",
                            ["Seleccioná sucursal", *BRANCHES],
                            value=rx.cond(
                                PurchaseState.sucursal != "",
                                PurchaseState.sucursal,
                                "Seleccioná sucursal",
                            ),
                            on_change=PurchaseState.set_sucursal,
                        ),
                        labeled_native_select(
                            "Producto",
                            PurchaseState.product_options,
                            name="producto",
                            on_change=PurchaseState.set_product_label,
                        ),
                        rx.form(
                            rx.hstack(
                                rx.input(
                                    name="qty",
                                    placeholder="Cantidad",
                                    default_value="1",
                                    type="number",
                                    step="0.01",
                                    min="0.01",
                                    size="3",
                                ),
                                rx.input(
                                    name="costo",
                                    placeholder="Costo unitario",
                                    type="number",
                                    step="0.01",
                                    min="0.01",
                                    size="3",
                                    required=True,
                                ),
                                rx.button("Agregar", type="submit", size="3"),
                                width="100%",
                            ),
                            key=PurchaseState.line_form_key,
                            on_submit=PurchaseState.add_line,
                            reset_on_submit=False,
                            width="100%",
                        ),
                        rx.foreach(PurchaseState.draft_names, lambda name: rx.badge(name, variant="soft")),
                        rx.text("Total: ", PurchaseState.draft_total_fmt, weight="bold"),
                        rx.hstack(
                            rx.switch(
                                checked=PurchaseState.registrar_gasto,
                                on_change=PurchaseState.set_registrar_gasto,
                            ),
                            rx.text("Registrar también como gasto"),
                        ),
                        labeled_native_select(
                            "Pago del gasto",
                            list(PAYMENT_METHODS),
                            on_change=PurchaseState.set_metodo_pago,
                        ),
                        rx.hstack(
                            rx.dialog.close(
                                rx.button(
                                    "Cancelar",
                                    variant="soft",
                                    on_click=PurchaseState.close_dialog,
                                )
                            ),
                            rx.button("Confirmar compra", on_click=PurchaseState.save),
                            justify="end",
                            width="100%",
                        ),
                        spacing="3",
                        width="100%",
                    ),
                    key=PurchaseState.form_key,
                    width="100%",
                ),
            ),
            open=PurchaseState.dialog_open,
            on_open_change=PurchaseState.set_dialog_open,
        ),
        table_wrap(
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell("Fecha"),
                        rx.table.column_header_cell("Proveedor"),
                        rx.table.column_header_cell("Sucursal"),
                        rx.table.column_header_cell("Total"),
                        rx.table.column_header_cell("Usuario"),
                        rx.table.column_header_cell(""),
                    )
                ),
                rx.table.body(
                    rx.foreach(
                        PurchaseState.items,
                        lambda p: rx.table.row(
                            rx.table.cell(p.fecha),
                            rx.table.cell(p.proveedor),
                            rx.table.cell(p.sucursal),
                            rx.table.cell(p.total_fmt),
                            rx.table.cell(p.usuario),
                            rx.table.cell(delete_button(PurchaseState.delete_item(p.id))),
                        ),
                    )
                ),
                width="100%",
                variant="surface",
            )
        ),
    )


def sellers_page() -> rx.Component:
    return app_shell(
        "Vendedores",
        rx.cond(
            AuthState.is_admin,
            rx.button("Nuevo vendedor", on_click=SellerState.open_new, size="3"),
            rx.fragment(),
        ),
        rx.dialog.root(
            rx.dialog.content(
                rx.dialog.title("Vendedor"),
                rx.vstack(
                    labeled_input("Nombre", value=SellerState.form_nombre, on_change=SellerState.set_form_nombre),
                    labeled_input("Apellido", value=SellerState.form_apellido, on_change=SellerState.set_form_apellido),
                    labeled_input("Email", value=SellerState.form_email, on_change=SellerState.set_form_email),
                    labeled_input("Contraseña", type="password", value=SellerState.form_password, on_change=SellerState.set_form_password),
                    rx.hstack(rx.switch(checked=SellerState.form_activo, on_change=SellerState.set_form_activo), rx.text("Activo")),
                    rx.hstack(
                        rx.dialog.close(rx.button("Cancelar", variant="soft", on_click=SellerState.close_dialog)),
                        rx.button("Guardar", on_click=SellerState.save),
                        justify="end",
                        width="100%",
                    ),
                    spacing="3",
                    width="100%",
                ),
            ),
            open=SellerState.dialog_open,
            on_open_change=SellerState.set_dialog_open,
        ),
        table_wrap(
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell("Nombre"),
                        rx.table.column_header_cell("Email"),
                        rx.table.column_header_cell("Rol"),
                        rx.table.column_header_cell("Hoy"),
                        rx.table.column_header_cell("Mes"),
                        rx.table.column_header_cell("Estado"),
                        rx.table.column_header_cell(""),
                    )
                ),
                rx.table.body(
                    rx.foreach(
                        SellerState.items,
                        lambda u: rx.table.row(
                            rx.table.cell(u.nombre),
                            rx.table.cell(u.email),
                            rx.table.cell(u.role_label),
                            rx.table.cell(u.ventas_dia_fmt),
                            rx.table.cell(u.ventas_mes_fmt),
                            rx.table.cell(rx.cond(u.activo, rx.badge("Activo", color_scheme="green"), rx.badge("Inactivo", color_scheme="gray"))),
                            rx.table.cell(
                                rx.cond(
                                    AuthState.is_admin,
                                    rx.button("Editar", size="1", variant="soft", on_click=SellerState.open_edit(u.id)),
                                    rx.fragment(),
                                )
                            ),
                        ),
                    )
                ),
                width="100%",
                variant="surface",
            )
        ),
    )


def sales_page() -> rx.Component:
    return app_shell(
        "Ventas",
        rx.flex(
            *[
                rx.button(
                    label,
                    size="2",
                    variant=rx.cond(SalesListState.period == key, "solid", "soft"),
                    on_click=SalesListState.set_period(key),
                )
                for key, label in PERIODS
                if key != "personalizado"
            ],
            rx.select(
                ["Todos", *PAYMENT_METHODS],
                value=rx.cond(SalesListState.metodo_pago == "", "Todos", SalesListState.metodo_pago),
                on_change=SalesListState.set_metodo,
                size="2",
            ),
            spacing="2",
            wrap="wrap",
        ),
        table_wrap(
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell("Fecha"),
                        rx.table.column_header_cell("Número"),
                        rx.table.column_header_cell("Vendedor"),
                        rx.table.column_header_cell("Sucursal"),
                        rx.table.column_header_cell("Total"),
                        rx.table.column_header_cell("Pago"),
                        rx.table.column_header_cell("Ganancia"),
                        rx.table.column_header_cell("Tipo"),
                        rx.table.column_header_cell("Observación"),
                        rx.table.column_header_cell(""),
                    )
                ),
                rx.table.body(
                    rx.foreach(
                        SalesListState.items,
                        lambda s: rx.table.row(
                            rx.table.cell(s.fecha),
                            rx.table.cell(s.numero),
                            rx.table.cell(s.vendedor),
                            rx.table.cell(s.sucursal),
                            rx.table.cell(s.total_fmt),
                            rx.table.cell(s.metodo_pago),
                            rx.table.cell(s.ganancia_fmt),
                            rx.table.cell(s.tipo),
                            rx.table.cell(s.observacion),
                            rx.table.cell(delete_button(SalesListState.delete_item(s.id))),
                        ),
                    )
                ),
                width="100%",
                variant="surface",
            )
        ),
    )


def reports_page() -> rx.Component:
    return app_shell(
        "Reportes",
        rx.hstack(
            rx.input(type="date", value=ReportState.start, on_change=ReportState.set_start, size="3"),
            rx.input(type="date", value=ReportState.end, on_change=ReportState.set_end, size="3"),
            rx.button("Consultar", on_click=ReportState.reload, size="3"),
            wrap="wrap",
        ),
        rx.hstack(
            rx.button("Ventas", variant=rx.cond(ReportState.tab == "ventas", "solid", "soft"), on_click=ReportState.set_tab("ventas")),
            rx.button("Gastos", variant=rx.cond(ReportState.tab == "gastos", "solid", "soft"), on_click=ReportState.set_tab("gastos")),
            rx.button("Productos", variant=rx.cond(ReportState.tab == "productos", "solid", "soft"), on_click=ReportState.set_tab("productos")),
            rx.button("Vendedores", variant=rx.cond(ReportState.tab == "vendedores", "solid", "soft"), on_click=ReportState.set_tab("vendedores")),
            wrap="wrap",
        ),
        rx.match(
            ReportState.tab,
            (
                "ventas",
                table_wrap(
                    rx.table.root(
                        rx.table.header(rx.table.row(
                            rx.table.column_header_cell("Fecha"),
                            rx.table.column_header_cell("Número"),
                            rx.table.column_header_cell("Vendedor"),
                            rx.table.column_header_cell("Sucursal"),
                            rx.table.column_header_cell("Total"),
                            rx.table.column_header_cell("Pago"),
                            rx.table.column_header_cell("Ganancia"),
                            rx.table.column_header_cell("Observación"),
                        )),
                        rx.table.body(rx.foreach(ReportState.sales, lambda s: rx.table.row(
                            rx.table.cell(s.fecha), rx.table.cell(s.numero), rx.table.cell(s.vendedor),
                            rx.table.cell(s.sucursal), rx.table.cell(s.total_fmt), rx.table.cell(s.metodo_pago),
                            rx.table.cell(s.ganancia_fmt), rx.table.cell(s.observacion),
                        ))),
                        width="100%", variant="surface",
                    )
                ),
            ),
            (
                "gastos",
                table_wrap(
                    rx.table.root(
                        rx.table.header(rx.table.row(
                            rx.table.column_header_cell("Fecha"),
                            rx.table.column_header_cell("Categoría"),
                            rx.table.column_header_cell("Descripción"),
                            rx.table.column_header_cell("Sucursal"),
                            rx.table.column_header_cell("Importe"),
                        )),
                        rx.table.body(rx.foreach(ReportState.expenses, lambda e: rx.table.row(
                            rx.table.cell(e.fecha), rx.table.cell(e.categoria), rx.table.cell(e.descripcion), rx.table.cell(e.sucursal), rx.table.cell(e.importe_fmt),
                        ))),
                        width="100%", variant="surface",
                    )
                ),
            ),
            (
                "productos",
                table_wrap(
                    rx.table.root(
                        rx.table.header(rx.table.row(
                            rx.table.column_header_cell("Producto"),
                            rx.table.column_header_cell("Cantidad"),
                            rx.table.column_header_cell("Facturación"),
                            rx.table.column_header_cell("Costo"),
                            rx.table.column_header_cell("Ganancia"),
                        )),
                        rx.table.body(rx.foreach(ReportState.products, lambda p: rx.table.row(
                            rx.table.cell(p.producto), rx.table.cell(p.cantidad), rx.table.cell(p.facturacion_fmt),
                            rx.table.cell(p.costo_fmt), rx.table.cell(p.ganancia_fmt),
                        ))),
                        width="100%", variant="surface",
                    )
                ),
            ),
            table_wrap(
                rx.table.root(
                    rx.table.header(rx.table.row(
                        rx.table.column_header_cell("Vendedor"),
                        rx.table.column_header_cell("Ventas"),
                        rx.table.column_header_cell("Facturación"),
                        rx.table.column_header_cell("Ganancia"),
                    )),
                    rx.table.body(rx.foreach(ReportState.sellers, lambda s: rx.table.row(
                        rx.table.cell(s.vendedor), rx.table.cell(s.cantidad), rx.table.cell(s.facturacion_fmt), rx.table.cell(s.ganancia_fmt),
                    ))),
                    width="100%", variant="surface",
                )
            ),
        ),
    )


def users_page() -> rx.Component:
    return app_shell(
        "Usuarios",
        rx.button("Nuevo usuario", on_click=UsersAdminState.open_new, size="3"),
        rx.dialog.root(
            rx.dialog.content(
                rx.dialog.title("Usuario"),
                rx.vstack(
                    labeled_input("Nombre", value=UsersAdminState.form_nombre, on_change=UsersAdminState.set_form_nombre),
                    labeled_input("Apellido", value=UsersAdminState.form_apellido, on_change=UsersAdminState.set_form_apellido),
                    labeled_input("Email", value=UsersAdminState.form_email, on_change=UsersAdminState.set_form_email),
                    labeled_input("Contraseña", type="password", value=UsersAdminState.form_password, on_change=UsersAdminState.set_form_password),
                    labeled_select("Rol", list(ROLE_LABELS.keys()), value=UsersAdminState.form_role, on_change=UsersAdminState.set_form_role),
                    rx.hstack(rx.switch(checked=UsersAdminState.form_activo, on_change=UsersAdminState.set_form_activo), rx.text("Activo")),
                    rx.hstack(
                        rx.dialog.close(rx.button("Cancelar", variant="soft", on_click=UsersAdminState.close_dialog)),
                        rx.button("Guardar", on_click=UsersAdminState.save),
                        justify="end",
                        width="100%",
                    ),
                    spacing="3",
                    width="100%",
                ),
            ),
            open=UsersAdminState.dialog_open,
            on_open_change=UsersAdminState.set_dialog_open,
        ),
        table_wrap(
            rx.table.root(
                rx.table.header(rx.table.row(
                    rx.table.column_header_cell("Nombre"),
                    rx.table.column_header_cell("Email"),
                    rx.table.column_header_cell("Rol"),
                    rx.table.column_header_cell("Última actividad"),
                    rx.table.column_header_cell("Estado"),
                    rx.table.column_header_cell(""),
                )),
                rx.table.body(rx.foreach(UsersAdminState.items, lambda u: rx.table.row(
                    rx.table.cell(u.nombre),
                    rx.table.cell(u.email),
                    rx.table.cell(u.role_label),
                    rx.table.cell(u.last_activity),
                    rx.table.cell(rx.cond(u.activo, rx.badge("Activo", color_scheme="green"), rx.badge("Inactivo", color_scheme="gray"))),
                    rx.table.cell(rx.hstack(
                        rx.button("Editar", size="1", variant="soft", on_click=UsersAdminState.open_edit(u.id)),
                        rx.button(rx.cond(u.activo, "Desactivar", "Activar"), size="1", variant="ghost", on_click=UsersAdminState.toggle_active(u.id)),
                        delete_button(UsersAdminState.delete_item(u.id)),
                    )),
                ))),
                width="100%", variant="surface",
            )
        ),
    )


def settings_page() -> rx.Component:
    return app_shell(
        "Configuración",
        rx.card(
            rx.vstack(
                labeled_input("Nombre del comercio", value=SettingsState.nombre_comercio, on_change=SettingsState.set_nombre_comercio),
                labeled_input("Slogan", value=SettingsState.slogan, on_change=SettingsState.set_slogan),
                labeled_input("Teléfono", value=SettingsState.telefono, on_change=SettingsState.set_telefono),
                labeled_input("Dirección", value=SettingsState.direccion, on_change=SettingsState.set_direccion),
                labeled_input("CUIT", value=SettingsState.cuit, on_change=SettingsState.set_cuit),
                rx.grid(
                    labeled_input("Moneda", value=SettingsState.moneda, on_change=SettingsState.set_moneda),
                    labeled_input("Símbolo", value=SettingsState.simbolo, on_change=SettingsState.set_simbolo),
                    columns="2",
                    spacing="3",
                    width="100%",
                ),
                labeled_input("URL del logo", value=SettingsState.logo_url, on_change=SettingsState.set_logo_url),
                rx.button("Guardar configuración", on_click=SettingsState.save, size="3"),
                spacing="4",
                width="100%",
                max_width="640px",
            ),
            size="3",
        ),
    )


def cash_page() -> rx.Component:
    return app_shell(
        "Cierre de caja",
        rx.grid(
            kpi_card("Efectivo", CashState.efectivo_fmt, "banknote", "green"),
            kpi_card("Transferencias", CashState.transferencias_fmt, "arrow-left-right", "blue"),
            kpi_card("Tarjetas", CashState.tarjetas_fmt, "credit-card", "violet"),
            kpi_card("Gastos", CashState.gastos_fmt, "wallet", "red"),
            kpi_card("Ganancia neta", CashState.total_fmt, "piggy-bank", "teal"),
            kpi_card("Operaciones", CashState.operaciones, "hash", "amber"),
            columns=rx.breakpoints(initial="1", sm="2", lg="3"),
            spacing="3",
            width="100%",
        ),
        rx.card(
            rx.vstack(
                rx.heading("Cerrar jornada", size="5"),
                rx.text("Efectivo esperado: ", CashState.efectivo_fmt),
                labeled_input("Efectivo contado", value=CashState.efectivo_contado, on_change=CashState.set_efectivo_contado),
                rx.text("Diferencia: ", CashState.diferencia_live_fmt, weight="bold"),
                labeled_input("Observaciones", value=CashState.observaciones, on_change=CashState.set_observaciones),
                rx.button("Guardar cierre", on_click=CashState.close_register, size="3"),
                spacing="3",
                width="100%",
                max_width="480px",
            ),
            size="3",
        ),
        table_wrap(
            rx.table.root(
                rx.table.header(rx.table.row(
                    rx.table.column_header_cell("Fecha"),
                    rx.table.column_header_cell("Efectivo"),
                    rx.table.column_header_cell("Transferencia"),
                    rx.table.column_header_cell("Tarjeta"),
                    rx.table.column_header_cell("Gasto"),
                    rx.table.column_header_cell("Total"),
                )),
                rx.table.body(rx.foreach(CashState.history, lambda c: rx.table.row(
                    rx.table.cell(c.fecha),
                    rx.table.cell(c.efectivo_fmt),
                    rx.table.cell(c.transferencias_fmt),
                    rx.table.cell(c.tarjetas_fmt),
                    rx.table.cell(c.gastos_fmt),
                    rx.table.cell(c.total_fmt),
                ))),
                width="100%", variant="surface",
            )
        ),
    )
