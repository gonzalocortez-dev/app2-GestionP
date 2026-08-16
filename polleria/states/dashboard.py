"""Dashboard: KPIs, gráficos y filtro temporal."""

from __future__ import annotations

from typing import Any

import reflex as rx

from polleria.auth.state import AuthState
from polleria.constants import PERIOD_LABELS
from polleria.schemas import RankRow
from polleria.services.core import DatabaseUnavailable
from polleria.services import queries
from polleria.utils.time import iso_date, period_range, today_ar


class DashboardState(AuthState):
    period: str = "hoy"
    custom_start: str = ""
    custom_end: str = ""
    loading: bool = False

    facturacion_fmt: str = "$0,00"
    ganancia_bruta_fmt: str = "$0,00"
    ganancia_neta_fmt: str = "$0,00"
    gastos_fmt: str = "$0,00"
    costo_fmt: str = "$0,00"
    operaciones: int = 0
    ticket_fmt: str = "$0,00"
    ventas_rapidas_fmt: str = "$0,00"
    hay_ventas_rapidas: bool = False

    series: list[dict[str, Any]] = []
    payments: list[dict[str, Any]] = []
    sellers: list[dict[str, Any]] = []
    ranking: list[RankRow] = []

    @rx.var(cache=True)
    def period_label(self) -> str:
        return PERIOD_LABELS.get(self.period, "Hoy")

    @rx.var(cache=True)
    def is_custom(self) -> bool:
        return self.period == "personalizado"

    @rx.event
    def on_load(self):
        self._bootstrap()
        if not self.is_authenticated:
            return rx.redirect("/login")
        self.custom_start = iso_date(today_ar())
        self.custom_end = iso_date(today_ar())
        self.refresh()

    @rx.event
    def set_period(self, value: str):
        self.period = value
        self.refresh()

    @rx.event
    def set_custom_start(self, value: str):
        self.custom_start = value

    @rx.event
    def set_custom_end(self, value: str):
        self.custom_end = value

    @rx.event
    def refresh(self):
        self.loading = True
        start, end = period_range(self.period, self.custom_start, self.custom_end)
        own = self.is_vendedor
        vid = self.authenticated_user.id if own else None
        try:
            with rx.session() as db:
                kpis = queries.dashboard_kpis(
                    db, start, end, vendedor_id=vid, own_only=own
                )
                self.facturacion_fmt = kpis["facturacion_fmt"]
                self.ganancia_bruta_fmt = kpis["ganancia_bruta_fmt"]
                self.ganancia_neta_fmt = kpis["ganancia_neta_fmt"]
                self.gastos_fmt = kpis["gastos_fmt"]
                self.costo_fmt = kpis["costo_fmt"]
                self.operaciones = kpis["operaciones"]
                self.ticket_fmt = kpis["ticket_fmt"]
                self.ventas_rapidas_fmt = kpis["ventas_rapidas_fmt"]
                self.hay_ventas_rapidas = kpis["hay_ventas_rapidas"]
                self.series = queries.sales_by_day(db, start, end)
                self.payments = queries.sales_by_payment(db, start, end)
                self.sellers = queries.sales_by_seller(db, start, end)
                self.ranking = [RankRow(**p) for p in queries.top_products(db, start, end)]
        except Exception as exc:
            self.loading = False
            raise DatabaseUnavailable(str(exc)) from exc
        self.loading = False
