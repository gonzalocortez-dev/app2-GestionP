"""Corrige conflicto npm EOVERRIDE entre postcss directo y overrides."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / ".web" / "package.json"


def main() -> None:
    if not PKG.exists():
        return
    data = json.loads(PKG.read_text(encoding="utf-8"))
    overrides = data.get("overrides") or {}
    if overrides.get("postcss") == "8.5.23":
        overrides["postcss"] = "$postcss"
        data["overrides"] = overrides
        PKG.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        print(f"Corregido override postcss en {PKG}")


if __name__ == "__main__":
    main()
