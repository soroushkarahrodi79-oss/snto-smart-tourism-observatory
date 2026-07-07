"""CI guard: la versión del pie de README debe coincidir con pyproject.toml."""
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
