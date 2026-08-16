"""Evita npm EBUSY al remover paquetes en Windows + OneDrive."""

from __future__ import annotations

from pathlib import Path

TARGET = (
    Path(__file__).resolve().parents[1]
    / ".venv"
    / "Lib"
    / "site-packages"
    / "reflex"
    / "utils"
    / "js_runtimes.py"
)

OLD = """    to_remove = stale_packages | misplaced_in_dev | misplaced_in_deps
    if to_remove:
        run_package_manager(
            [
                primary_package_manager,
                "remove",
                "--legacy-peer-deps",
                *sorted(to_remove),
            ],
            show_status_message="Removing unused frontend packages",
        )"""

NEW = """    to_remove = stale_packages | misplaced_in_dev | misplaced_in_deps
    # Windows/OneDrive locks node_modules during npm remove (EBUSY).
    if to_remove and not constants.IS_WINDOWS:
        run_package_manager(
            [
                primary_package_manager,
                "remove",
                "--legacy-peer-deps",
                *sorted(to_remove),
            ],
            show_status_message="Removing unused frontend packages",
        )"""


def main() -> None:
    if not TARGET.exists():
        print("No se encontró reflex en .venv; omitiendo parche EBUSY.")
        return
    text = TARGET.read_text(encoding="utf-8")
    if NEW in text:
        print("Parche npm EBUSY ya aplicado.")
        return
    if OLD not in text:
        if "if to_remove and not constants.IS_WINDOWS:" in text:
            print("Parche npm EBUSY ya aplicado (variante).")
            return
        print("Reflex cambió js_runtimes.py; revisar manualmente el parche EBUSY.")
        return
    TARGET.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
    print(f"Parche EBUSY aplicado en {TARGET}")


if __name__ == "__main__":
    main()
