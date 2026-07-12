"""CI guards for the canonical project version."""
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).parent.parent


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
