from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version


def _read_from_pyproject() -> str:
    import tomllib
    from pathlib import Path

    with open(Path(__file__).parent.parent / "pyproject.toml", "rb") as f:
        return tomllib.load(f)["project"]["version"]  # type: ignore[return-value]


try:
    __version__: str = _pkg_version("snto")
except PackageNotFoundError:
    # Package not installed (running directly from source without pip install -e .)
    __version__ = _read_from_pyproject()
