"""Stock por sucursal. Product.stock queda como total sincronizado."""

from __future__ import annotations

from sqlmodel import Session, select

from polleria.constants import BRANCHES
from polleria.models import BranchStock, Product
from polleria.services.core import BusinessError


def _fmt(qty: float) -> str:
    return str(round(qty or 0, 3)).replace(".", ",")


def stock_estado(qty: float, minimo: float) -> str:
    if (qty or 0) <= 0:
        return "sin_stock"
    if (qty or 0) <= (minimo or 0):
        return "stock_bajo"
    return "stock_normal"


def get_or_create_branch_stock(db: Session, product_id: int, sucursal: str) -> BranchStock:
    branch = (sucursal or "").strip()
    if branch not in BRANCHES:
        raise BusinessError("Seleccioná la sucursal.")
    row = db.exec(
        select(BranchStock).where(
            BranchStock.product_id == product_id,
            BranchStock.sucursal == branch,
        )
    ).first()
    if row is None:
        row = BranchStock(product_id=product_id, sucursal=branch, cantidad=0)
        db.add(row)
        db.flush()
    return row


def ensure_product_branches(db: Session, product_id: int) -> None:
    existing = {
        r.sucursal
        for r in db.exec(
            select(BranchStock).where(BranchStock.product_id == product_id)
        ).all()
    }
    for branch in BRANCHES:
        if branch not in existing:
            db.add(BranchStock(product_id=product_id, sucursal=branch, cantidad=0))
    db.flush()


def sync_product_total(db: Session, product: Product) -> float:
    rows = db.exec(
        select(BranchStock).where(BranchStock.product_id == product.id)
    ).all()
    total = round(sum(r.cantidad or 0 for r in rows), 3)
    product.stock = total
    db.add(product)
    return total


def qty_at(db: Session, product_id: int, sucursal: str) -> float:
    row = db.exec(
        select(BranchStock).where(
            BranchStock.product_id == product_id,
            BranchStock.sucursal == sucursal,
        )
    ).first()
    return float(row.cantidad or 0) if row else 0.0


def stocks_by_product(db: Session, product_ids: list[int]) -> dict[int, dict[str, float]]:
    out: dict[int, dict[str, float]] = {pid: {b: 0.0 for b in BRANCHES} for pid in product_ids}
    if not product_ids:
        return out
    rows = db.exec(select(BranchStock).where(BranchStock.product_id.in_(product_ids))).all()
    for row in rows:
        if row.product_id in out:
            out[row.product_id][row.sucursal] = float(row.cantidad or 0)
    return out


def branch_fmts(by_branch: dict[str, float] | None) -> tuple[str, str, str]:
    data = by_branch or {}
    return (
        _fmt(data.get(BRANCHES[0], 0)),
        _fmt(data.get(BRANCHES[1], 0) if len(BRANCHES) > 1 else 0),
        _fmt(data.get(BRANCHES[2], 0) if len(BRANCHES) > 2 else 0),
    )


def seed_legacy_branch_stocks(db: Session) -> None:
    """Copia el stock global viejo a la primera sucursal, una sola vez."""
    products = db.exec(select(Product)).all()
    if not products:
        return
    existing = {
        (r.product_id, r.sucursal)
        for r in db.exec(select(BranchStock)).all()
    }
    if existing:
        for product in products:
            ensure_product_branches(db, product.id or 0)
            sync_product_total(db, product)
        db.commit()
        return
    for product in products:
        pid = product.id or 0
        leftover = float(product.stock or 0)
        for i, branch in enumerate(BRANCHES):
            qty = leftover if i == 0 else 0.0
            db.add(BranchStock(product_id=pid, sucursal=branch, cantidad=qty))
    db.commit()
