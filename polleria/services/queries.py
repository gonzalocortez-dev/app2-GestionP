"""Consultas de dashboard, reportes y cierre de caja."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta

from sqlmodel import Session, func, select

from polleria.models import Expense, Product, Sale, SaleItem, User
from polleria.utils.money import money, round_money
from polleria.utils.time import format_dt, to_ar


def _sales_q(start: datetime, end: datetime, vendedor_id: int | None = None, own_only: bool = False):
    q = select(Sale).where(
        Sale.fecha >= start,
        Sale.fecha < end,
        Sale.estado == "completada",
    )
    if vendedor_id is not None and own_only:
        q = q.where(Sale.vendedor_id == vendedor_id)
    return q


def dashboard_kpis(
    db: Session,
    start: datetime,
    end: datetime,
    *,
    vendedor_id: int | None = None,
    own_only: bool = False,
) -> dict:
    sales = db.exec(_sales_q(start, end, vendedor_id, own_only)).all()
    expenses_q = select(Expense).where(Expense.fecha >= start, Expense.fecha < end)
    expenses = db.exec(expenses_q).all()

    facturacion = round_money(sum(s.total for s in sales))
    costo = round_money(sum(s.costo_total for s in sales if s.tiene_costo))
    ganancia_bruta = round_money(sum(s.ganancia for s in sales if s.tiene_costo))
    gastos = round_money(sum(e.monto for e in expenses))
    ventas_rapidas = round_money(sum(s.total for s in sales if s.is_quick))
    ganancia_neta = round_money(ganancia_bruta - gastos)
    ops = len(sales)
    ticket = round_money(facturacion / ops) if ops else 0.0

    return {
        "facturacion": facturacion,
        "facturacion_fmt": money(facturacion),
        "costo": costo,
        "costo_fmt": money(costo),
        "ganancia_bruta": ganancia_bruta,
        "ganancia_bruta_fmt": money(ganancia_bruta),
        "gastos": gastos,
        "gastos_fmt": money(gastos),
        "ganancia_neta": ganancia_neta,
        "ganancia_neta_fmt": money(ganancia_neta),
        "ventas_rapidas": ventas_rapidas,
        "ventas_rapidas_fmt": money(ventas_rapidas),
        "operaciones": ops,
        "ticket_fmt": money(ticket),
        "hay_ventas_rapidas": ventas_rapidas > 0,
    }


def sales_by_day(db: Session, start: datetime, end: datetime) -> list[dict]:
    sales = db.exec(
        select(Sale).where(Sale.fecha >= start, Sale.fecha < end, Sale.estado == "completada")
    ).all()
    bucket: dict[str, dict] = {}
    cursor = start.date()
    last = (end - timedelta(seconds=1)).date()
    while cursor <= last:
        key = cursor.isoformat()
        bucket[key] = {
            "fecha": cursor.strftime("%d/%m"),
            "ventas": 0.0,
            "ganancia": 0.0,
        }
        cursor += timedelta(days=1)
    for sale in sales:
        key = to_ar(sale.fecha).date().isoformat()
        if key in bucket:
            bucket[key]["ventas"] = round_money(bucket[key]["ventas"] + sale.total)
            if sale.tiene_costo:
                bucket[key]["ganancia"] = round_money(bucket[key]["ganancia"] + sale.ganancia)
    return list(bucket.values())


def sales_by_payment(db: Session, start: datetime, end: datetime) -> list[dict]:
    sales = db.exec(
        select(Sale).where(Sale.fecha >= start, Sale.fecha < end, Sale.estado == "completada")
    ).all()
    totals: dict[str, float] = defaultdict(float)
    for sale in sales:
        totals[sale.metodo_pago] += sale.total
    colors = {
        "Efectivo": "#16a34a",
        "Transferencia": "#2563eb",
        "Débito": "#7c3aed",
        "Crédito": "#db2777",
        "Mercado Pago": "#0891b2",
        "Otro": "#64748b",
    }
    return [
        {"name": name, "value": round_money(value), "fill": colors.get(name, "#ea580c")}
        for name, value in totals.items()
        if value > 0
    ]


def sales_by_seller(db: Session, start: datetime, end: datetime) -> list[dict]:
    rows = db.exec(
        select(
            User.nombre,
            User.apellido,
            func.coalesce(func.sum(Sale.total), 0),
        )
        .join(Sale, Sale.vendedor_id == User.id)
        .where(Sale.fecha >= start, Sale.fecha < end, Sale.estado == "completada")
        .group_by(User.nombre, User.apellido)
        .order_by(func.sum(Sale.total).desc())
    ).all()
    return [
        {
            "vendedor": f"{nombre} {apellido}".strip(),
            "total": round_money(float(total or 0)),
        }
        for nombre, apellido, total in rows
    ]


def top_products(db: Session, start: datetime, end: datetime, limit: int = 5) -> list[dict]:
    rows = db.exec(
        select(
            Product.nombre,
            func.coalesce(func.sum(SaleItem.cantidad), 0),
            func.coalesce(func.sum(SaleItem.subtotal), 0),
            func.coalesce(
                func.sum((SaleItem.precio_unitario - SaleItem.costo_unitario) * SaleItem.cantidad),
                0,
            ),
        )
        .join(SaleItem, SaleItem.product_id == Product.id)
        .join(Sale, Sale.id == SaleItem.sale_id)
        .where(Sale.fecha >= start, Sale.fecha < end, Sale.estado == "completada")
        .group_by(Product.id, Product.nombre)
        .order_by(func.sum(SaleItem.cantidad).desc())
        .limit(limit)
    ).all()
    ranking = []
    for idx, (nombre, qty, fact, gain) in enumerate(rows, start=1):
        ranking.append(
            {
                "puesto": str(idx),
                "producto": nombre,
                "cantidad": round(float(qty or 0), 2),
                "facturacion_fmt": money(float(fact or 0)),
                "ganancia_fmt": money(float(gain or 0)),
            }
        )
    return ranking


def report_sales(
    db: Session,
    start: datetime,
    end: datetime,
    *,
    vendedor_id: int | None = None,
    metodo_pago: str = "",
    only_vendedor: int | None = None,
) -> list[dict]:
    q = select(Sale, User).join(User, User.id == Sale.vendedor_id).where(
        Sale.fecha >= start,
        Sale.fecha < end,
        Sale.estado == "completada",
    )
    if vendedor_id:
        q = q.where(Sale.vendedor_id == vendedor_id)
    if only_vendedor:
        q = q.where(Sale.vendedor_id == only_vendedor)
    if metodo_pago:
        q = q.where(Sale.metodo_pago == metodo_pago)
    q = q.order_by(Sale.fecha.desc())
    rows = []
    for sale, user in db.exec(q).all():
        rows.append(
            {
                "id": sale.id,
                "fecha": format_dt(sale.fecha),
                "numero": f"#{sale.id:05d}",
                "vendedor": user.nombre_completo,
                "total_fmt": money(sale.total),
                "metodo_pago": sale.metodo_pago,
                "ganancia_fmt": money(sale.ganancia) if sale.tiene_costo else "N/D",
                "tipo": "Rápida" if sale.is_quick else "Detallada",
            }
        )
    return rows


def report_expenses(db: Session, start: datetime, end: datetime) -> list[dict]:
    rows = db.exec(
        select(Expense)
        .where(Expense.fecha >= start, Expense.fecha < end)
        .order_by(Expense.fecha.desc())
    ).all()
    return [
        {
            "id": e.id,
            "fecha": format_dt(e.fecha),
            "categoria": e.categoria,
            "descripcion": e.descripcion,
            "importe_fmt": money(e.monto),
        }
        for e in rows
    ]


def report_products(db: Session, start: datetime, end: datetime, product_id: int | None = None) -> list[dict]:
    q = (
        select(
            Product.nombre,
            func.coalesce(func.sum(SaleItem.cantidad), 0),
            func.coalesce(func.sum(SaleItem.subtotal), 0),
            func.coalesce(func.sum(SaleItem.costo_unitario * SaleItem.cantidad), 0),
            func.coalesce(
                func.sum((SaleItem.precio_unitario - SaleItem.costo_unitario) * SaleItem.cantidad),
                0,
            ),
        )
        .join(SaleItem, SaleItem.product_id == Product.id)
        .join(Sale, Sale.id == SaleItem.sale_id)
        .where(Sale.fecha >= start, Sale.fecha < end, Sale.estado == "completada")
        .group_by(Product.id, Product.nombre)
        .order_by(func.sum(SaleItem.subtotal).desc())
    )
    if product_id:
        q = q.where(Product.id == product_id)
    return [
        {
            "producto": nombre,
            "cantidad": round(float(qty or 0), 2),
            "facturacion_fmt": money(float(fact or 0)),
            "costo_fmt": money(float(cost or 0)),
            "ganancia_fmt": money(float(gain or 0)),
        }
        for nombre, qty, fact, cost, gain in db.exec(q).all()
    ]


def report_sellers(db: Session, start: datetime, end: datetime) -> list[dict]:
    rows = db.exec(
        select(
            User.nombre,
            User.apellido,
            func.count(Sale.id),
            func.coalesce(func.sum(Sale.total), 0),
            func.coalesce(func.sum(Sale.ganancia), 0),
        )
        .join(Sale, Sale.vendedor_id == User.id)
        .where(Sale.fecha >= start, Sale.fecha < end, Sale.estado == "completada")
        .group_by(User.nombre, User.apellido)
        .order_by(func.sum(Sale.total).desc())
    ).all()
    return [
        {
            "vendedor": f"{nombre} {apellido}".strip(),
            "cantidad": int(count or 0),
            "facturacion_fmt": money(float(total or 0)),
            "ganancia_fmt": money(float(gain or 0)),
        }
        for nombre, apellido, count, total, gain in rows
    ]


def cash_totals(db: Session, start: datetime, end: datetime, vendedor_id: int | None = None) -> dict:
    q = select(Sale).where(Sale.fecha >= start, Sale.fecha < end, Sale.estado == "completada")
    if vendedor_id:
        q = q.where(Sale.vendedor_id == vendedor_id)
    sales = db.exec(q).all()
    by_method: dict[str, float] = defaultdict(float)
    for sale in sales:
        by_method[sale.metodo_pago] += sale.total
    tarjetas = by_method.get("Débito", 0) + by_method.get("Crédito", 0)
    return {
        "efectivo": round_money(by_method.get("Efectivo", 0)),
        "efectivo_fmt": money(by_method.get("Efectivo", 0)),
        "transferencias": round_money(by_method.get("Transferencia", 0)),
        "transferencias_fmt": money(by_method.get("Transferencia", 0)),
        "tarjetas": round_money(tarjetas),
        "tarjetas_fmt": money(tarjetas),
        "mercadopago": round_money(by_method.get("Mercado Pago", 0)),
        "mercadopago_fmt": money(by_method.get("Mercado Pago", 0)),
        "total": round_money(sum(s.total for s in sales)),
        "total_fmt": money(sum(s.total for s in sales)),
        "operaciones": len(sales),
    }
