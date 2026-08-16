"""Modelos relacionales de PostgreSQL."""

from __future__ import annotations

from datetime import datetime

import bcrypt
import reflex as rx
import sqlalchemy as sa
from sqlmodel import Field


def _ts(*, onupdate: bool = False) -> sa.Column:
    kwargs: dict = {
        "type_": sa.DateTime(timezone=True),
        "server_default": sa.func.now(),
        "nullable": False,
    }
    if onupdate:
        kwargs["onupdate"] = sa.func.now()
    return sa.Column(**kwargs)


class User(rx.Model, table=True):
    __tablename__ = "users"

    nombre: str
    apellido: str = ""
    email: str = Field(index=True, unique=True)
    password_hash: str
    role: str = Field(default="vendedor", index=True)
    activo: bool = Field(default=True, index=True)
    email_verified: bool = Field(default=False, index=True)
    last_activity: datetime | None = Field(default=None)
    created_at: datetime | None = Field(default=None, sa_column=_ts())
    updated_at: datetime | None = Field(default=None, sa_column=_ts(onupdate=True))

    @staticmethod
    def hash_password(secret: str) -> str:
        return bcrypt.hashpw(secret.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    @staticmethod
    def is_bcrypt_hash(value: str) -> bool:
        return (
            value.startswith(("$2a$", "$2b$", "$2y$"))
            and len(value) == 60
        )

    def verify_password(self, secret: str) -> bool:
        stored = self.password_hash or ""
        if self.is_bcrypt_hash(stored):
            try:
                return bcrypt.checkpw(
                    secret.encode("utf-8"),
                    stored.encode("utf-8"),
                )
            except ValueError:
                return False
        return secret == stored

    def needs_password_hash(self) -> bool:
        return not self.is_bcrypt_hash(self.password_hash or "")

    @property
    def nombre_completo(self) -> str:
        return f"{self.nombre} {self.apellido}".strip()


class AuthSession(rx.Model, table=True):
    __tablename__ = "auth_sessions"

    user_id: int = Field(foreign_key="users.id", index=True)
    session_id: str = Field(unique=True, index=True)
    expiration: datetime = Field(
        sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False)
    )


class EmailToken(rx.Model, table=True):
    __tablename__ = "email_tokens"

    user_id: int = Field(foreign_key="users.id", index=True)
    token_hash: str = Field(index=True)
    purpose: str = Field(index=True)  # verify | reset
    expiration: datetime = Field(
        sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False)
    )
    used: bool = Field(default=False, index=True)
    created_at: datetime | None = Field(default=None, sa_column=_ts())


class Product(rx.Model, table=True):
    __tablename__ = "products"

    nombre: str = Field(index=True)
    descripcion: str = ""
    categoria: str = Field(default="Pollo", index=True)
    unidad_medida: str = Field(default="Kg")
    precio_venta: float = 0.0
    costo: float = 0.0
    stock: float = 0.0
    stock_minimo: float = 0.0
    activo: bool = Field(default=True, index=True)
    created_at: datetime | None = Field(default=None, sa_column=_ts())
    updated_at: datetime | None = Field(default=None, sa_column=_ts(onupdate=True))

    @property
    def valor_inventario(self) -> float:
        return round(self.stock * self.costo, 2)

    @property
    def stock_estado(self) -> str:
        if self.stock <= 0:
            return "sin_stock"
        if self.stock <= self.stock_minimo:
            return "stock_bajo"
        return "stock_normal"


class Sale(rx.Model, table=True):
    __tablename__ = "sales"

    vendedor_id: int = Field(foreign_key="users.id", index=True)
    created_by: int | None = Field(default=None, foreign_key="users.id")
    fecha: datetime = Field(
        sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False, index=True)
    )
    subtotal: float = 0.0
    descuento: float = 0.0
    total: float = 0.0
    costo_total: float = 0.0
    ganancia: float = 0.0
    tiene_costo: bool = True
    is_quick: bool = False
    metodo_pago: str = Field(default="Efectivo", index=True)
    estado: str = Field(default="completada", index=True)
    observacion: str = ""
    created_at: datetime | None = Field(default=None, sa_column=_ts())


class SaleItem(rx.Model, table=True):
    __tablename__ = "sale_items"

    sale_id: int = Field(foreign_key="sales.id", index=True)
    product_id: int = Field(foreign_key="products.id", index=True)
    cantidad: float
    precio_unitario: float
    costo_unitario: float = 0.0
    subtotal: float


class Supplier(rx.Model, table=True):
    __tablename__ = "suppliers"

    nombre: str = Field(index=True)
    telefono: str = ""
    notas: str = ""
    activo: bool = True
    created_at: datetime | None = Field(default=None, sa_column=_ts())


class Purchase(rx.Model, table=True):
    __tablename__ = "purchases"

    proveedor: str = ""
    supplier_id: int | None = Field(default=None, foreign_key="suppliers.id")
    fecha: datetime = Field(
        sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False, index=True)
    )
    total: float = 0.0
    usuario_id: int = Field(foreign_key="users.id", index=True)
    registrar_gasto: bool = True
    observaciones: str = ""
    created_at: datetime | None = Field(default=None, sa_column=_ts())


class PurchaseItem(rx.Model, table=True):
    __tablename__ = "purchase_items"

    purchase_id: int = Field(foreign_key="purchases.id", index=True)
    product_id: int = Field(foreign_key="products.id", index=True)
    cantidad: float
    costo_unitario: float
    subtotal: float


class Expense(rx.Model, table=True):
    __tablename__ = "expenses"

    categoria: str = Field(index=True)
    descripcion: str = ""
    monto: float
    fecha: datetime = Field(
        sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False, index=True)
    )
    metodo_pago: str = Field(default="Efectivo")
    usuario_id: int = Field(foreign_key="users.id", index=True)
    observaciones: str = ""
    purchase_id: int | None = Field(default=None, foreign_key="purchases.id")
    created_at: datetime | None = Field(default=None, sa_column=_ts())


class InventoryMovement(rx.Model, table=True):
    __tablename__ = "inventory_movements"

    product_id: int = Field(foreign_key="products.id", index=True)
    tipo: str = Field(index=True)
    cantidad: float
    motivo: str = ""
    usuario_id: int = Field(foreign_key="users.id", index=True)
    fecha: datetime = Field(
        sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False, index=True)
    )
    referencia: str = ""


class CashRegisterClosure(rx.Model, table=True):
    __tablename__ = "cash_register_closures"

    usuario_id: int = Field(foreign_key="users.id", index=True)
    fecha: datetime = Field(
        sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False, index=True)
    )
    efectivo_esperado: float = 0.0
    efectivo_contado: float = 0.0
    diferencia: float = 0.0
    total_ventas: float = 0.0
    total_transferencias: float = 0.0
    total_tarjetas: float = 0.0
    total_mercadopago: float = 0.0
    cantidad_operaciones: int = 0
    observaciones: str = ""
    created_at: datetime | None = Field(default=None, sa_column=_ts())


class BusinessSettings(rx.Model, table=True):
    __tablename__ = "business_settings"

    nombre_comercio: str = "Mi Pollería"
    slogan: str = ""
    telefono: str = ""
    direccion: str = ""
    cuit: str = ""
    moneda: str = "ARS"
    simbolo_moneda: str = "$"
    logo_url: str = ""
    updated_at: datetime | None = Field(default=None, sa_column=_ts(onupdate=True))


class AuditLog(rx.Model, table=True):
    __tablename__ = "audit_logs"

    usuario_id: int | None = Field(default=None, foreign_key="users.id", index=True)
    accion: str = Field(index=True)
    entidad: str = ""
    entidad_id: int | None = None
    detalle: str = ""
    created_at: datetime | None = Field(default=None, sa_column=_ts())
