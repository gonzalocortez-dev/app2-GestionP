"""Punto de venta optimizado para tablet."""

from __future__ import annotations

import reflex as rx

from polleria.components.layout import app_shell
from polleria.components.widgets import empty_state
from polleria.constants import PAYMENT_METHODS
from polleria.states.pos import POSState


def _product_card(product) -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.badge(product.categoria, variant="soft", color_scheme="orange"),
                rx.spacer(),
                rx.text(product.unidad_medida, size="1", color=rx.color("slate", 10)),
                width="100%",
            ),
            rx.text(product.nombre, weight="bold", size="4"),
            rx.hstack(
                rx.heading(product.precio_fmt, size="5", color=rx.color("orange", 11)),
                rx.spacer(),
                rx.text(f"Stock {product.stock_fmt}", size="1", color=rx.color("slate", 10)),
                width="100%",
            ),
            rx.button(
                "Agregar",
                on_click=POSState.add_product(product.id),
                size="3",
                width="100%",
                height="44px",
            ),
            spacing="2",
            width="100%",
            align="start",
        ),
        size="2",
        on_click=POSState.add_product(product.id),
        cursor="pointer",
        _hover={"transform": "translateY(-1px)", "box_shadow": "0 8px 20px rgba(15,23,42,0.08)"},
        width="100%",
    )


def _cart_row(item) -> rx.Component:
    return rx.hstack(
        rx.vstack(
            rx.text(item.nombre, weight="medium", size="2"),
            rx.text(item.precio_fmt, size="1", color=rx.color("slate", 10)),
            spacing="0",
            align="start",
        ),
        rx.hstack(
            rx.icon_button(
                rx.icon("minus", size=16),
                size="2",
                variant="soft",
                on_click=POSState.bump_qty(item.product_id, -1),
            ),
            rx.text(item.cantidad_fmt, width="2.2rem", text_align="center", weight="bold"),
            rx.icon_button(
                rx.icon("plus", size=16),
                size="2",
                variant="soft",
                on_click=POSState.bump_qty(item.product_id, 1),
            ),
            spacing="1",
        ),
        rx.text(item.subtotal_fmt, weight="bold", min_width="5.5rem", text_align="right"),
        rx.icon_button(
            rx.icon("trash-2", size=16),
            size="2",
            variant="ghost",
            color_scheme="red",
            on_click=POSState.remove_item(item.product_id),
        ),
        width="100%",
        align="center",
        padding="0.45rem 0",
        border_bottom=f"1px solid {rx.color('slate', 4)}",
    )


def cart_panel() -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.heading("Carrito", size="5"),
                rx.badge(POSState.cart_count, color_scheme="orange"),
                rx.spacer(),
                rx.button("Vaciar", variant="ghost", size="1", on_click=POSState.clear_cart),
                width="100%",
            ),
            rx.cond(
                POSState.cart_count > 0,
                rx.vstack(
                    rx.foreach(POSState.cart, _cart_row),
                    width="100%",
                    max_height="280px",
                    overflow_y="auto",
                ),
                empty_state("Tocá un producto para agregarlo", "shopping-cart"),
            ),
            rx.divider(),
            rx.hstack(rx.text("Subtotal"), rx.spacer(), rx.text(POSState.subtotal_fmt), width="100%"),
            rx.hstack(
                rx.text("Descuento"),
                rx.input(
                    value=POSState.discount_input,
                    on_change=POSState.set_discount_input,
                    width="120px",
                    size="2",
                    text_align="right",
                ),
                width="100%",
                justify="between",
            ),
            rx.hstack(
                rx.heading("TOTAL", size="4"),
                rx.spacer(),
                rx.heading(POSState.total_fmt, size="6", color=rx.color("orange", 11)),
                width="100%",
            ),
            rx.select(
                list(PAYMENT_METHODS),
                value=POSState.metodo_pago,
                on_change=POSState.set_metodo_pago,
                size="3",
                width="100%",
            ),
            rx.input(
                placeholder="Observación (opcional)",
                value=POSState.observacion,
                on_change=POSState.set_observacion,
                size="3",
                width="100%",
            ),
            rx.button(
                "Cobrar venta",
                on_click=POSState.confirm_sale,
                size="4",
                width="100%",
                height="56px",
                color_scheme="orange",
            ),
            spacing="3",
            width="100%",
        ),
        size="2",
        width="100%",
        position=["relative", "relative", "sticky"],
        top="1rem",
    )


def quick_panel() -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.callout(
                "La venta rápida registra el importe sin productos, stock ni costo de mercadería.",
                icon="zap",
                color="amber",
            ),
            rx.input(
                placeholder="Importe de la venta",
                value=POSState.quick_amount,
                on_change=POSState.set_quick_amount,
                size="3",
                width="100%",
                height="52px",
            ),
            rx.select(
                list(PAYMENT_METHODS),
                value=POSState.metodo_pago,
                on_change=POSState.set_metodo_pago,
                size="3",
                width="100%",
            ),
            rx.input(
                placeholder="Observación",
                value=POSState.observacion,
                on_change=POSState.set_observacion,
                size="3",
                width="100%",
            ),
            rx.button(
                "Registrar venta rápida",
                on_click=POSState.confirm_sale,
                size="4",
                width="100%",
                height="56px",
            ),
            spacing="4",
            width="100%",
        ),
        size="3",
        width="100%",
        max_width="560px",
    )


def confirm_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Venta registrada correctamente"),
            rx.vstack(
                rx.heading(POSState.last_total, size="8", color=rx.color("orange", 11)),
                rx.text(f"Operación {POSState.last_numero}"),
                rx.text(f"Vendedor: {POSState.last_vendedor}"),
                rx.text(f"Pago: {POSState.last_pago}"),
                rx.text(f"Fecha: {POSState.last_fecha}"),
                spacing="2",
            ),
            rx.dialog.close(
                rx.button("Nueva venta", on_click=POSState.close_confirm, size="3", width="100%"),
            ),
            max_width="420px",
        ),
        open=POSState.show_confirm,
        on_open_change=POSState.set_show_confirm,
    )


def pos_page() -> rx.Component:
    return app_shell(
        "Punto de Venta",
        rx.hstack(
            rx.button(
                "Venta detallada",
                variant=rx.cond(POSState.is_quick, "soft", "solid"),
                on_click=POSState.set_mode("detallada"),
                size="2",
            ),
            rx.button(
                "Venta rápida",
                variant=rx.cond(POSState.is_quick, "solid", "soft"),
                on_click=POSState.set_mode("rapida"),
                size="2",
            ),
            spacing="2",
        ),
        confirm_dialog(),
        rx.grid(
            rx.vstack(
                rx.hstack(
                    rx.cond(
                        POSState.seller_locked,
                        rx.badge(POSState.seller_label, size="3", color_scheme="orange"),
                        rx.select(
                            POSState.seller_options,
                            value=POSState.seller_label,
                            on_change=POSState.set_seller_label,
                            size="3",
                            width="100%",
                        ),
                    ),
                    rx.input(type="date", value=POSState.sale_date, on_change=POSState.set_sale_date, size="3"),
                    width="100%",
                    spacing="2",
                    wrap="wrap",
                ),
                rx.cond(
                    POSState.is_quick,
                    quick_panel(),
                    rx.fragment(
                        rx.hstack(
                            rx.input(
                                placeholder="Buscar producto o categoría",
                                value=POSState.search,
                                on_change=POSState.set_search,
                                size="3",
                                width="100%",
                                height="48px",
                            ),
                            rx.input(
                                placeholder="Cant.",
                                value=POSState.qty_input,
                                on_change=POSState.set_qty_input,
                                size="3",
                                width="110px",
                                height="48px",
                            ),
                            width="100%",
                            spacing="2",
                        ),
                        rx.cond(
                            POSState.filtered_products.length() > 0,
                            rx.grid(
                                rx.foreach(POSState.filtered_products, _product_card),
                                columns=rx.breakpoints(initial="2", md="2", lg="3"),
                                spacing="3",
                                width="100%",
                            ),
                            empty_state("No hay productos para esa búsqueda", "search"),
                        ),
                    ),
                ),
                spacing="4",
                width="100%",
                align="start",
            ),
            rx.cond(~POSState.is_quick, cart_panel(), rx.fragment()),
            columns=rx.breakpoints(initial="1", md="2"),
            spacing="4",
            width="100%",
        ),
    )
