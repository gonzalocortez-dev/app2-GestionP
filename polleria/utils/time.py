"""Fechas y zona horaria de Argentina."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

AR_TZ = ZoneInfo("America/Argentina/Buenos_Aires")
UTC = timezone.utc


def now_ar() -> datetime:
    return datetime.now(AR_TZ)


def now_utc() -> datetime:
    return datetime.now(UTC)


def today_ar() -> date:
    return now_ar().date()


def as_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=AR_TZ)
    return dt


def to_ar(dt: datetime) -> datetime:
    return as_aware(dt).astimezone(AR_TZ)


def start_of_day(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, tzinfo=AR_TZ)


def end_of_day(d: date) -> datetime:
    return start_of_day(d) + timedelta(days=1)


def period_range(
    period: str,
    custom_start: str = "",
    custom_end: str = "",
) -> tuple[datetime, datetime]:
    """Devuelve [inicio, fin) en zona Argentina para el período pedido."""
    today = today_ar()
    if period == "ayer":
        d = today - timedelta(days=1)
        return start_of_day(d), end_of_day(d)
    if period == "semana":
        monday = today - timedelta(days=today.weekday())
        return start_of_day(monday), end_of_day(today)
    if period == "mes":
        return start_of_day(today.replace(day=1)), end_of_day(today)
    if period == "mes_anterior":
        first_this = today.replace(day=1)
        last_prev = first_this - timedelta(days=1)
        first_prev = last_prev.replace(day=1)
        return start_of_day(first_prev), start_of_day(first_this)
    if period == "personalizado":
        try:
            s = date.fromisoformat(custom_start) if custom_start else today
        except ValueError:
            s = today
        try:
            e = date.fromisoformat(custom_end) if custom_end else today
        except ValueError:
            e = today
        if e < s:
            s, e = e, s
        return start_of_day(s), end_of_day(e)
    return start_of_day(today), end_of_day(today)


def parse_date(value: str | None, fallback: date | None = None) -> date:
    if value:
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            pass
    return fallback or today_ar()


def format_dt(dt: datetime | None) -> str:
    if dt is None:
        return "—"
    local = to_ar(dt)
    return local.strftime("%d/%m/%Y %H:%M")


def format_date(d: date | datetime | None) -> str:
    if d is None:
        return "—"
    if isinstance(d, datetime):
        d = to_ar(d).date()
    return d.strftime("%d/%m/%Y")


def iso_date(d: date | None = None) -> str:
    return (d or today_ar()).isoformat()
