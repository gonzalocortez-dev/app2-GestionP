"""Dashboard principal con KPIs y gráficos."""

from __future__ import annotations

import reflex as rx

from polleria.auth.state import AuthState
from polleria.components.layout import app_shell
from polleria.components.widgets import empty_state, kpi_card, section_card
from polleria.constants import PERIODS
from polleria.states.dashboard import DashboardState


def period_chips() -> rx.Component:
    return rx.flex(
        *[
            rx.button(
                label,
                variant=rx.cond(DashboardState.period == key, "solid", "soft"),
                color_scheme="orange",
                size="2",
                on_click=DashboardState.set_period(key),
            )
            for key, label in PERIODS
        ],
        rx.button("Actualizar", variant="outline", size="2", on_click=DashboardState.refresh),
        spacing="2",
        wrap="wrap",
        width="100%",
    )


def dashboard_page() -> rx.Component:
    return app_shell(
        "Dashboard",
        period_chips(),
        rx.cond(
            DashboardState.is_custom,
            rx.hstack(
                rx.input(type="date", value=DashboardState.custom_start, on_change=DashboardState.set_custom_start),
                rx.input(type="date", value=DashboardState.custom_end, on_change=DashboardState.set_custom_end),
                rx.button("Aplicar", on_click=DashboardState.refresh, size="2"),
                wrap="wrap",
            ),
            rx.fragment(),
        ),
        rx.grid(
            kpi_card("Ventas del período", DashboardState.facturacion_fmt, "banknote", "orange"),
            rx.cond(
                AuthState.can_see_profits,
                kpi_card("Ganancia bruta", DashboardState.ganancia_bruta_fmt, "trending-up", "green"),
                kpi_card("Ticket promedio", DashboardState.ticket_fmt, "receipt", "blue"),
            ),
            kpi_card("Gastos del período", DashboardState.gastos_fmt, "wallet", "red"),
            rx.cond(
                AuthState.can_see_profits,
                kpi_card("Ganancia neta estimada", DashboardState.ganancia_neta_fmt, "piggy-bank", "teal"),
                kpi_card("Operaciones", DashboardState.operaciones, "hash", "blue"),
            ),
            kpi_card("Costo de mercadería", DashboardState.costo_fmt, "package", "amber"),
            kpi_card("Cantidad de ventas", DashboardState.operaciones, "shopping-bag", "violet"),
            columns=rx.breakpoints(initial="1", sm="2", lg="3"),
            spacing="3",
            width="100%",
        ),
        rx.cond(
            DashboardState.hay_ventas_rapidas,
            rx.callout(
                "Hay ventas rápidas en el período. No se estima costo ni ganancia sobre esas operaciones.",
                icon="info",
                color="amber",
            ),
            rx.fragment(),
        ),
        rx.grid(
            section_card(
                rx.heading("Ventas por día", size="5"),
                rx.recharts.area_chart(
                    rx.recharts.area(data_key="ventas", stroke="#ea580c", fill="#fdba74", type_="monotone"),
                    rx.recharts.x_axis(data_key="fecha"),
                    rx.recharts.y_axis(),
                    rx.recharts.cartesian_grid(stroke_dasharray="3 3"),
                    rx.recharts.graphing_tooltip(),
                    data=DashboardState.series,
                    width="100%",
                    height=280,
                ),
            ),
            rx.cond(
                AuthState.can_see_profits,
                section_card(
                    rx.heading("Ganancias por día", size="5"),
                    rx.recharts.line_chart(
                        rx.recharts.line(data_key="ganancia", stroke="#16a34a", type_="monotone"),
                        rx.recharts.x_axis(data_key="fecha"),
                        rx.recharts.y_axis(),
                        rx.recharts.cartesian_grid(stroke_dasharray="3 3"),
                        rx.recharts.graphing_tooltip(),
                        data=DashboardState.series,
                        width="100%",
                        height=280,
                    ),
                ),
                section_card(
                    rx.heading("Actividad", size="5"),
                    rx.text("Las ganancias detalladas están disponibles para administrador y supervisor."),
                ),
            ),
            columns=rx.breakpoints(initial="1", lg="2"),
            spacing="3",
            width="100%",
        ),
        rx.grid(
            section_card(
                rx.heading("Métodos de pago", size="5"),
                rx.cond(
                    DashboardState.payments.length() > 0,
                    rx.recharts.pie_chart(
                        rx.recharts.pie(
                            data=DashboardState.payments,
                            data_key="value",
                            name_key="name",
                            inner_radius="55%",
                            outer_radius="80%",
                            padding_angle=3,
                        ),
                        rx.recharts.legend(),
                        rx.recharts.graphing_tooltip(),
                        width="100%",
                        height=280,
                    ),
                    empty_state("Sin ventas en el período", "pie-chart"),
                ),
            ),
            section_card(
                rx.heading("Ventas por vendedor", size="5"),
                rx.cond(
                    DashboardState.sellers.length() > 0,
                    rx.recharts.bar_chart(
                        rx.recharts.bar(data_key="total", fill="#ea580c", radius=[6, 6, 0, 0]),
                        rx.recharts.x_axis(data_key="vendedor"),
                        rx.recharts.y_axis(),
                        rx.recharts.graphing_tooltip(),
                        data=DashboardState.sellers,
                        width="100%",
                        height=280,
                    ),
                    empty_state("Sin datos de vendedores", "users"),
                ),
            ),
            columns=rx.breakpoints(initial="1", lg="2"),
            spacing="3",
            width="100%",
        ),
        section_card(
            rx.heading("Productos más vendidos", size="5"),
            rx.cond(
                DashboardState.ranking.length() > 0,
                rx.vstack(
                    rx.foreach(
                        DashboardState.ranking,
                        lambda row: rx.hstack(
                            rx.badge(row.puesto, color_scheme="orange"),
                            rx.text(row.producto, weight="medium"),
                            rx.spacer(),
                            rx.text(row.facturacion_fmt, color=rx.color("slate", 11)),
                            width="100%",
                            padding="0.6rem 0",
                            border_bottom=f"1px solid {rx.color('slate', 4)}",
                        ),
                    ),
                    width="100%",
                ),
                empty_state("Todavía no hay ranking de productos", "utensils"),
            ),
        ),
    )
