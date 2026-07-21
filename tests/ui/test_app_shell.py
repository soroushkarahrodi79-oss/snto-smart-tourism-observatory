"""Contract between the navigation registry and the app.py dispatch shell.

The 4-layer shell (Fase 6) declares its modules in ``src/ui/navigation.py`` and
dispatches them in ``app.py`` by ``NavigationModule.key``. Two agents touch both
files, so a module can drift out of sync — declared but never wired (blank
tab), or a branch left behind after a module is removed (dead code). These
tests read app.py's source statically (no heavy Streamlit render) and fail
loudly on either drift, and check every audience view opens on a real layer.
"""
from __future__ import annotations

import re
from pathlib import Path

from src.platform.views import get_view, view_modes
from src.ui.navigation import NAVIGATION_LAYERS, navigation_layer

_APP_SRC = (Path(__file__).resolve().parents[2] / "app.py").read_text(
    encoding="utf-8"
)


def _declared_module_keys() -> set[str]:
    return {m.key for layer in NAVIGATION_LAYERS for m in layer.modules}


def _dispatched_module_keys() -> set[str]:
    return set(re.findall(r'_module\.key == "([a-z_]+)"', _APP_SRC))


def test_every_declared_module_is_wired_in_app() -> None:
    missing = _declared_module_keys() - _dispatched_module_keys()
    assert not missing, f"navigation modules declared but unwired in app.py: {missing}"


def test_no_orphan_dispatch_branch_in_app() -> None:
    orphan = _dispatched_module_keys() - _declared_module_keys()
    assert not orphan, f"app.py dispatches modules not in navigation: {orphan}"


def test_app_still_raises_on_an_unknown_module_key() -> None:
    # The shell must keep its explicit guard so a future unwired module fails
    # loudly instead of rendering an empty tab.
    assert "Unknown navigation module" in _APP_SRC


def test_every_view_opens_on_a_real_layer() -> None:
    for mode in view_modes():
        view = get_view(mode)
        # Raises ValueError if the home layer is not a real navigation layer.
        navigation_layer(view.home_layer)
