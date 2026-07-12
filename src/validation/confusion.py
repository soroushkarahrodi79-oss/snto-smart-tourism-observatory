"""
SNTO — Satellite ↔ field confusion matrix (F5 / issue #26)
==========================================================
The correlation and BACI contrast in ``agreement.py`` answer *"does the
satellite signal track degradation on a continuous scale?"*. This module
answers the operational question a director actually asks: *"when the satellite
raises an alert on an asset, is the asset really degraded on the ground?"* —
i.e. the **confusion matrix** of the binary decision.

Positive class = **alert / degraded**. For each asset that has *both* a
satellite verdict and a field verdict we cross-tabulate:

    * satellite alert  = significant decreasing NDVI trend (``AssetTrend.is_alert``);
    * field degraded   = field degradation index at/above a threshold.

From the 2×2 table we report accuracy, precision, recall, F1 and **Cohen's
kappa** (chance-corrected agreement — the honest metric when the classes are
imbalanced, as they will be in a small first campaign).

Pure functions, no third-party dependency. This module supplies the machinery;
it does **not** contain field data. A confusion matrix is only meaningful once a
real field campaign has produced ground-truth verdicts (see
``docs/field_validation_protocol.md``); until then ``n`` is 0 and the report
says so rather than inventing agreement.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, Sequence

if TYPE_CHECKING:
    from src.platform.satellite_trends import AssetTrend

# Field degradation index (0-100 stress) at/above which a plot is "degraded".
FIELD_DEGRADED_THRESHOLD = 50.0


def satellite_alert(trend: AssetTrend) -> bool:
    """Satellite verdict: True when the asset shows significant degradation."""
    return trend.is_alert


def field_degraded(
    degradation_index: Optional[float],
    threshold: float = FIELD_DEGRADED_THRESHOLD,
) -> Optional[bool]:
    """Field verdict from a degradation index; ``None`` when no datum exists."""
    if degradation_index is None:
        return None
    return degradation_index >= threshold


@dataclass(frozen=True)
class ConfusionReport:
    """2×2 agreement between satellite alert and field-degraded verdicts."""
    n: int
    tp: int  # satellite alert & field degraded
    fp: int  # satellite alert & field NOT degraded (false alarm)
    fn: int  # no satellite alert & field degraded (missed)
    tn: int  # no satellite alert & field NOT degraded
    accuracy: Optional[float]
    precision: Optional[float]
    recall: Optional[float]
    f1: Optional[float]
    cohen_kappa: Optional[float]
    verdict: str


def _safe_ratio(num: float, den: float) -> Optional[float]:
    return round(num / den, 4) if den else None


def confusion_matrix(pairs: Sequence[tuple[bool, bool]]) -> ConfusionReport:
    """Build the confusion report from ``(satellite_alert, field_degraded)`` pairs.

    Each pair is one asset with both verdicts present. With no pairs the report
    is empty (``n=0``) and states that agreement cannot be computed — the
    non-negotiable is to never fabricate validation evidence.
    """
    n = len(pairs)
    if n == 0:
        return ConfusionReport(
            0, 0, 0, 0, 0, None, None, None, None, None,
            "sin pares co-localizados: ejecutar campaña de campo primero",
        )
    tp = sum(1 for s, f in pairs if s and f)
    fp = sum(1 for s, f in pairs if s and not f)
    fn = sum(1 for s, f in pairs if not s and f)
    tn = sum(1 for s, f in pairs if not s and not f)

    accuracy = _safe_ratio(tp + tn, n)
    precision = _safe_ratio(tp, tp + fp)
    recall = _safe_ratio(tp, tp + fn)
    f1 = (
        _safe_ratio(2 * precision * recall, precision + recall)
        if precision and recall else (0.0 if (precision == 0 or recall == 0)
                                      and (tp + fp) and (tp + fn) else None)
    )
    kappa = _cohen_kappa(tp, fp, fn, tn, n)

    if n < 3:
        verdict = "muestra mínima: indicativo, no concluyente (ampliar campaña)"
    elif kappa is not None and kappa >= 0.6:
        verdict = "acuerdo sustancial satélite↔campo"
    elif kappa is not None and kappa >= 0.2:
        verdict = "acuerdo débil/moderado: ampliar muestra"
    else:
        verdict = "sin acuerdo por encima del azar — revisar umbrales y muestreo"
    return ConfusionReport(
        n, tp, fp, fn, tn, accuracy, precision, recall, f1, kappa, verdict,
    )


def _cohen_kappa(
    tp: int, fp: int, fn: int, tn: int, n: int
) -> Optional[float]:
    """Chance-corrected agreement κ; ``None`` if undefined for this table."""
    po = (tp + tn) / n
    p_sat_pos = (tp + fp) / n
    p_field_pos = (tp + fn) / n
    pe = p_sat_pos * p_field_pos + (1 - p_sat_pos) * (1 - p_field_pos)
    if pe == 1.0:
        # Both raters constant and agreeing → perfect; else undefined.
        return 1.0 if po == 1.0 else 0.0
    return round((po - pe) / (1 - pe), 4)


def build_pairs(
    trends_by_id: dict[str, AssetTrend],
    field_index_by_id: dict[str, Optional[float]],
    threshold: float = FIELD_DEGRADED_THRESHOLD,
) -> list[tuple[bool, bool]]:
    """Co-locate satellite trends and field indices by asset id → verdict pairs.

    Only assets present in *both* maps and with a non-null field index yield a
    pair; the rest are skipped (never guessed).
    """
    pairs: list[tuple[bool, bool]] = []
    for asset_id, trend in trends_by_id.items():
        fd = field_degraded(field_index_by_id.get(asset_id), threshold)
        if fd is None:
            continue
        pairs.append((satellite_alert(trend), fd))
    return pairs
