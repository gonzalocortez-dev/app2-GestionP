"""Utilidades para formularios Reflex."""

from __future__ import annotations


def form_field(form_data: dict, key: str, fallback: str = "") -> str:
    raw = form_data.get(key, fallback)
    if isinstance(raw, list):
        raw = raw[0] if raw else fallback
    return str(raw or fallback).strip()
