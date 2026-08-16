"""Parchea Reflex 0.9 para evitar EOVERRIDE de postcss con npm 10+."""

from __future__ import annotations

from pathlib import Path

TARGET = (
    Path(__file__).resolve().parents[1]
    / ".venv"
    / "Lib"
    / "site-packages"
    / "reflex_base"
    / "constants"
    / "installer.py"
)

OLD = '"postcss": "8.5.23",'
NEW = '"postcss": "$postcss",'


def main() -> None:
    if not TARGET.exists():
        print("No se encontró reflex en .venv; omitiendo parche.")
        return
    text = TARGET.read_text(encoding="utf-8")
    if NEW in text:
        print("Parche postcss ya aplicado.")
        return
    if OLD not in text:
        print("Reflex cambió installer.py; revisar manualmente el override de postcss.")
        return
    TARGET.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
    print(f"Parche aplicado en {TARGET}")


if __name__ == "__main__":
    main()
