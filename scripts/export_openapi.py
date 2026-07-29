"""
scripts/export_openapi.py
=========================
Exporta el contrato **OpenAPI 3.1** de la API del SNTO a ``docs/api/openapi.json``
y lo mantiene sincronizado con el código.

Por qué existe (ADR-008, hoja de ruta v3.0 «Partner/integration ecosystem»): los
organismos gestores ya usan GIS/BI y esperan integrarse por HTTP. Publicar el
contrato permite **evaluar la integración sin desplegar nada** — el despliegue de
`/api/v2` sigue gobernado por ADR-012 y sus disparadores, que este script no
toca. El contrato es documentación, no infraestructura.

Uso:
    python scripts/export_openapi.py            # regenera el contrato
    python scripts/export_openapi.py --check    # CI: sale 1 si está desactualizado

Nota de versionado: el contrato incorpora la versión del paquete, así que un
cambio de versión lo deja obsoleto a propósito — regenerarlo forma parte del
flujo de release (junto a ``scripts/sync_readme.py``).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

CONTRACT = _ROOT / "docs" / "api" / "openapi.json"


def build_contract() -> dict:
    """Generate the OpenAPI schema from the live FastAPI app.

    Deterministic for a given code state (FastAPI derives it from the routers and
    Pydantic models), which is what lets ``--check`` gate CI without false alarms.
    """
    from src.api.main import app

    return app.openapi()


def serialise(contract: dict) -> str:
    """Stable JSON rendering: sorted keys + trailing newline, so a diff of the
    committed contract shows real API changes rather than dict ordering noise."""
    return json.dumps(contract, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="No escribe; sale 1 si el contrato comprometido está desactualizado.",
    )
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    rendered = serialise(build_contract())

    if args.check:
        if not CONTRACT.exists():
            print(
                f"[openapi] ERROR: falta {CONTRACT.relative_to(_ROOT)}.\n"
                "Ejecuta: python scripts/export_openapi.py"
            )
            return 1
        if CONTRACT.read_text(encoding="utf-8") != rendered:
            print(
                "[openapi] ERROR: el contrato comprometido no coincide con la API.\n"
                "Ejecuta: python scripts/export_openapi.py"
            )
            return 1
        print("[openapi] OK - el contrato coincide con la API")
        return 0

    CONTRACT.parent.mkdir(parents=True, exist_ok=True)
    if CONTRACT.exists() and CONTRACT.read_text(encoding="utf-8") == rendered:
        print("[openapi] Sin cambios: ya estaba al día")
        return 0

    CONTRACT.write_text(rendered, encoding="utf-8")
    print(f"[openapi] Actualizado {CONTRACT.relative_to(_ROOT)}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
