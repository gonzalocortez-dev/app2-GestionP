"""Filas serializables para tablas y gráficos."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ProductRow:
    id: int = 0
    nombre: str = ""
    descripcion: str = ""
    categoria: str = ""
    unidad_medida: str = "Kg"
    precio_venta: float = 0.0
    precio_fmt: str = "$0,00"
    costo: float = 0.0
    costo_fmt: str = "$0,00"
    stock: float = 0.0
    stock_fmt: str = "0"
    stock_minimo: float = 0.0
    valor_fmt: str = "$0,00"
    estado: str = "stock_normal"
    estado_label: str = "Stock normal"
    activo: bool = True


@dataclass
class CartItem:
    product_id: int = 0
    nombre: str = ""
    unidad: str = ""
    cantidad: float = 0.0
    cantidad_fmt: str = "0"
    precio_unitario: float = 0.0
    precio_fmt: str = "$0,00"
    costo_unitario: float = 0.0
    subtotal: float = 0.0
    subtotal_fmt: str = "$0,00"


@dataclass
class OptionItem:
    value: str = ""
    label: str = ""


@dataclass
class SaleRow:
    id: int = 0
    fecha: str = ""
    numero: str = ""
    vendedor: str = ""
    total_fmt: str = ""
    metodo_pago: str = ""
    ganancia_fmt: str = ""
    tipo: str = ""


@dataclass
class ExpenseRow:
    id: int = 0
    fecha: str = ""
    categoria: str = ""
    descripcion: str = ""
    importe_fmt: str = ""


@dataclass
class MovementRow:
    id: int = 0
    fecha: str = ""
    producto: str = ""
    tipo: str = ""
    cantidad_fmt: str = ""
    motivo: str = ""
    usuario: str = ""


@dataclass
class UserRow:
    id: int = 0
    nombre: str = ""
    email: str = ""
    role: str = ""
    role_label: str = ""
    activo: bool = True
    last_activity: str = "—"
    ventas_dia_fmt: str = "$0,00"
    ventas_mes_fmt: str = "$0,00"


@dataclass
class RankRow:
    puesto: str = ""
    producto: str = ""
    cantidad: float = 0.0
    facturacion_fmt: str = ""
    ganancia_fmt: str = ""


@dataclass
class ChartPoint:
    fecha: str = ""
    ventas: float = 0.0
    ganancia: float = 0.0


@dataclass
class PaymentSlice:
    name: str = ""
    value: float = 0.0
    fill: str = "#ea580c"


@dataclass
class SellerBar:
    vendedor: str = ""
    total: float = 0.0


@dataclass
class ReportProductRow:
    producto: str = ""
    cantidad: float = 0.0
    facturacion_fmt: str = ""
    costo_fmt: str = ""
    ganancia_fmt: str = ""


@dataclass
class ReportSellerRow:
    vendedor: str = ""
    cantidad: int = 0
    facturacion_fmt: str = ""
    ganancia_fmt: str = ""


@dataclass
class PurchaseRow:
    id: int = 0
    fecha: str = ""
    proveedor: str = ""
    total_fmt: str = ""
    usuario: str = ""


@dataclass
class ClosureRow:
    id: int = 0
    fecha: str = ""
    usuario: str = ""
    total_fmt: str = ""
    efectivo_esperado_fmt: str = ""
    efectivo_contado_fmt: str = ""
    diferencia_fmt: str = ""
