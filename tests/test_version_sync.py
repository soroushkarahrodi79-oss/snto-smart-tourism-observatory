"""CI guards for canonical project and publication metadata."""
import json
import re
import tomllib
from datetime import date
from pathlib import Path

from scripts.sync_readme import _apply_substitutions

ROOT = Path(__file__).parent.parent
ZENODO_CONCEPT_DOI = "10.5281/zenodo.20818269"
ZENODO_V2_CANONICAL_DOI = "10.5281/zenodo.21472647"
ZENODO_V2_RETIRED_DUPLICATE_DOI = "10.5281/zenodo.21512233"


def test_readme_version_matches_pyproject() -> None:
    with open(ROOT / "pyproject.toml", "rb") as f:
        version = tomllib.load(f)["project"]["version"]
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert f"SNTO v{version}" in readme, (
        f"README no contiene 'SNTO v{version}' (versión de pyproject.toml). "
        f"Ejecuta: python scripts/sync_readme.py"
    )


def test_citation_version_matches_pyproject() -> None:
    with open(ROOT / "pyproject.toml", "rb") as f:
        version = tomllib.load(f)["project"]["version"]
    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    match = re.search(r'^version:\s*["\']?([^"\'\s]+)', citation, re.MULTILINE)
    assert match is not None, "CITATION.cff debe declarar version"
    assert match.group(1) == version, (
        "CITATION.cff y pyproject.toml deben declarar la misma versión"
    )


def test_readme_and_citation_use_zenodo_concept_doi() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")

    assert ZENODO_CONCEPT_DOI in readme
    assert ZENODO_V2_CANONICAL_DOI in readme
    assert f'doi: "{ZENODO_CONCEPT_DOI}"' in citation
    assert f'value: "{ZENODO_CONCEPT_DOI}"' in citation
    assert ZENODO_V2_RETIRED_DUPLICATE_DOI not in readme
    assert ZENODO_V2_RETIRED_DUPLICATE_DOI not in citation


def test_zenodo_metadata_is_release_agnostic() -> None:
    metadata = json.loads((ROOT / ".zenodo.json").read_text(encoding="utf-8"))

    assert metadata["title"] == "SNTO — Smart Nature Tourism Observatory"
    assert "version" not in metadata, (
        "La versión de Zenodo debe proceder del tag de GitHub, no quedar fija"
    )


def test_readme_sync_preserves_count_when_pytest_is_unavailable() -> None:
    footer = (
        "<sub>SNTO v1.0.0 · Python ≥ 3.12 · 927 tests passing · junio 2026</sub>"
    )

    updated = _apply_substitutions(
        footer,
        version="2.1.0.dev0",
        count=None,
        today=date(2026, 7, 23),
    )

    assert updated == (
        "<sub>SNTO v2.1.0.dev0 · Python ≥ 3.12 · "
        "927 tests passing · julio 2026</sub>"
    )
