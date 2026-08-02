"""
SNTO — NDVI difference (dNDVI) builder (ADR-015)
================================================

Pure EE-object-in / EE-object-out. dNDVI = NDVI_after − NDVI_before.

Sign convention (documented and tested):

* **negative** dNDVI  → NDVI **decreased** between the two windows
  (vegetation loss / stress signal);
* **positive** dNDVI  → NDVI **increased** (greening / recovery);
* near-zero            → little change.

This is a *visual change* signal only. It is **not** a causal tourism-impact
metric and this phase assigns **no** severity thresholds or categories.

Both inputs come from SCL-masked composites (see :mod:`.composites`), so the
difference is consistently masked: a pixel invalid in either window is masked in
the result (EE ``subtract`` propagates masks).
"""
from __future__ import annotations

from typing import Any

from src.integrations.earth_engine.collections import DNDVI_BAND


def ndvi_difference(*, before_ndvi: Any, after_ndvi: Any) -> Any:
    """Return ``after_ndvi − before_ndvi`` as a single band named ``dNDVI``."""
    return after_ndvi.subtract(before_ndvi).rename(DNDVI_BAND)
