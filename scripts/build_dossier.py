"""
scripts/build_dossier.py
========================
Regenera los bloques derivados del dossier institucional OAPN
(``docs/dossier_institucional_OAPN.md``) desde las fuentes vivas del
observatorio, para que las cifras que se envían a la Dirección del Parque y a
EUROPARC no puedan volver a desviarse del sistema que describen.

Solo se sustituye el contenido entre marcadores::

    <!-- SNTO:AUTO:resultados -->
    ...contenido generado...
    <!-- /SNTO:AUTO:resultados -->

La prosa editorial (problema, propuesta, peticiones, contacto) es la voz
institucional del autor y **no** se toca.

Uso:
    python scripts/build_dossier.py            # regenera in situ
    python scripts/build_dossier.py --check    # CI: sale 1 si está desactualizado
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.reporting.institutional_dossier import (  # noqa: E402
    ALL_BLOCKS,
    build_dossier_blocks,
)

DOSSIER = _ROOT / "docs" / "dossier_institucional_OAPN.md"


def _marker_pattern(block: str) -> re.Pattern[str]:
    """Match a whole marked block, capturing the delimiters so they survive.

    The body is optional, so a freshly-marked document with adjacent markers (no
    content yet) still matches and gets filled on the first run.
    """
    return re.compile(
        rf"(<!-- SNTO:AUTO:{re.escape(block)} -->\n)"
        rf"(.*?)"
        rf"(<!-- /SNTO:AUTO:{re.escape(block)} -->)",
        re.DOTALL,
    )


def apply_blocks(text: str, blocks: dict[str, str]) -> str:
    """Replace each marked block's body with its generated content.

    Pure function (no I/O) so the substitution itself is unit-testable, mirroring
    ``scripts.sync_readme._apply_substitutions``. A block whose markers are absent
    from the document is skipped rather than appended — the caller decides whether
    that is an error (see :func:`missing_markers`).
    """
    for name, body in blocks.items():
        pattern = _marker_pattern(name)
        if pattern.search(text) is None:
            continue
        text = pattern.sub(
            lambda m, b=body: f"{m.group(1)}{b}\n{m.group(3)}", text
        )
    return text


def missing_markers(text: str, block_names: tuple[str, ...] = ALL_BLOCKS) -> list[str]:
    """Block names whose marker pair is not present in the document."""
    return [name for name in block_names if _marker_pattern(name).search(text) is None]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="No escribe; sale 1 si el dossier está desactualizado.",
    )
    parser.add_argument("--park", default="pnsg", help="Clave de territorio.")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    original = DOSSIER.read_text(encoding="utf-8")

    absent = missing_markers(original)
    if absent:
        print(
            f"[dossier] ERROR: faltan marcadores SNTO:AUTO en {DOSSIER.name}: "
            f"{', '.join(absent)}"
        )
        return 1

    blocks = build_dossier_blocks(args.park)
    updated = apply_blocks(original, blocks)

    if args.check:
        if updated != original:
            print(
                "[dossier] ERROR: el dossier institucional está desactualizado "
                "respecto a los datos vivos.\n"
                "Ejecuta: python scripts/build_dossier.py"
            )
            return 1
        print("[dossier] OK - el dossier coincide con los datos vivos")
        return 0

    if updated == original:
        print("[dossier] Sin cambios: ya estaba al día")
        return 0

    DOSSIER.write_text(updated, encoding="utf-8")
    print(f"[dossier] Actualizado {DOSSIER.relative_to(_ROOT)}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
