"""Per-asset data lineage contracts for the Phase 6 provenance workspace.

The current dashboard keeps values and source contracts, but it does not yet
persist one execution event or acquisition timestamp for every calculated
datum.  This module exposes the lineage that can be defended and leaves every
missing timestamp explicit instead of manufacturing audit metadata.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from src.platform.calibration import CalibrationResult
from src.platform.evidence import EvidenceClass
from src.platform.methodology import DataType
from src.territorial.models import TerritorialAsset


@dataclass(frozen=True)
class LineageRecord:
    """One displayed value and the source contract behind it."""

    datum: str
    value: str
    stage: str
    epistemic_type: DataType
    evidence_class: EvidenceClass
    source: str
    observed_at: str | None
    transformations: tuple[str, ...]
    location: str
    caveat: str


@dataclass(frozen=True)
class LineageProfile:
    """Auditable lineage surface for one managed asset."""

    asset_id: str
    asset_name: str
    records: tuple[LineageRecord, ...]

    @property
    def dated_records(self) -> int:
        return sum(record.observed_at is not None for record in self.records)

    @property
    def missing_dates(self) -> int:
        return len(self.records) - self.dated_records


def _ehs_record(
    asset: TerritorialAsset,
    calibration: CalibrationResult | None,
    scene_dates: Sequence[str],
) -> LineageRecord:
    satellite_override = (
        calibration is not None
        and calibration.flag == "mas_degradado"
        and calibration.satellite_ehs is not None
    )
    if satellite_override:
        trails = ", ".join(calibration.matched_trails) or "senda asociada"
        return LineageRecord(
            datum="EHS vigente",
            value=f"{asset.ehs:.1f} / 100",
            stage="Indicador",
            epistemic_type=DataType.CALCULATED,
            evidence_class=EvidenceClass.REAL,
            source=f"Sentinel-2 L2A sobre {trails}",
            observed_at=max(scene_dates) if scene_dates else None,
            transformations=(
                "NDVI/NDMI → EHS satelital",
                "Override conservador: solo escala degradación",
            ),
            location="src/platform/calibration.py",
            caveat=(
                "La fecha solo aparece si el producto .SAFE está disponible; "
                "no se sustituye por la fecha del informe."
            ),
        )
    return LineageRecord(
        datum="EHS vigente",
        value=f"{asset.ehs:.1f} / 100",
        stage="Indicador",
        epistemic_type=DataType.ESTIMATED,
        evidence_class=EvidenceClass.CALIBRATED,
        source="Inventario curado del activo, contrastado con Pipeline A",
        observed_at=None,
        transformations=(
            "Juicio experto → EHS curado",
            "Contraste satelital; nunca relaja el diagnóstico",
        ),
        location="src/platform/calibration.py",
        caveat="La fecha de valoración experta no se persiste por activo.",
    )


def build_lineage_profile(
    asset: TerritorialAsset,
    calibration: CalibrationResult | None = None,
    scene_dates: Sequence[str] = (),
) -> LineageProfile:
    """Build the honest data→indicator→decision chain for one asset."""
    action_label = (
        asset.recommended_action_label
        or asset.tier_label
        or "acción pendiente de etiquetar"
    )
    records = (
        _ehs_record(asset, calibration, scene_dates),
        LineageRecord(
            datum="Riesgo",
            value=f"{asset.risk_score:.2f} / 1",
            stage="Indicador",
            epistemic_type=DataType.CALCULATED,
            evidence_class=EvidenceClass.CALIBRATED,
            source="Motor de riesgo SNTO; entradas ecológicas y curadas",
            observed_at=None,
            transformations=("EHS + presión + vulnerabilidad → riesgo",),
            location="src/risk_engine/scorer.py",
            caveat="El runtime no persiste fecha ni huella de ejecución por valor.",
        ),
        LineageRecord(
            datum="DCS",
            value=f"{asset.dcs:.0f} / 100",
            stage="Indicador",
            epistemic_type=DataType.CALCULATED,
            evidence_class=EvidenceClass.CALIBRATED,
            source="Evaluador de confianza de decisión",
            observed_at=None,
            transformations=(
                "Calidad + tiempo + espacio + modelo + señal → DCS",
            ),
            location="src/decision_confidence/assessor.py",
            caveat="El total existe; los cinco componentes no están propagados.",
        ),
        LineageRecord(
            datum="Aforo anual de referencia",
            value=f"{asset.visitor_capacity_annual:,}".replace(",", "."),
            stage="Dato",
            epistemic_type=DataType.ESTIMATED,
            evidence_class=EvidenceClass.CALIBRATED,
            source="Atributo curado del activo; no es conteo de visitantes",
            observed_at=None,
            transformations=("Asignación experta de orden de magnitud",),
            location="src/territorial/fixtures.py",
            caveat="Sin fuente de aforo ni fecha persistidas por activo.",
        ),
        LineageRecord(
            datum="Importancia económica",
            value=f"{asset.economic_importance:.2f} / 1",
            stage="Dato",
            epistemic_type=DataType.ESTIMATED,
            evidence_class=EvidenceClass.CALIBRATED,
            source="Atributo estratégico curado",
            observed_at=None,
            transformations=("Normalización experta a escala 0–1",),
            location="src/territorial/fixtures.py",
            caveat="No equivale a actividad económica observada.",
        ),
        LineageRecord(
            datum="Accesibilidad",
            value=f"{asset.accessibility_score:.2f} / 1",
            stage="Dato",
            epistemic_type=DataType.ESTIMATED,
            evidence_class=EvidenceClass.CALIBRATED,
            source="Atributo estratégico curado",
            observed_at=None,
            transformations=("Valoración compuesta normalizada a 0–1",),
            location="src/territorial/fixtures.py",
            caveat="Sin medición de movilidad ni fecha persistida.",
        ),
        LineageRecord(
            datum="TPI",
            value="No calculado" if asset.tpi is None else f"{asset.tpi:.1f} / 100",
            stage="Indicador",
            epistemic_type=DataType.CALCULATED,
            evidence_class=EvidenceClass.CALIBRATED,
            source="Motor territorial SNTO; hereda la entrada más débil",
            observed_at=None,
            transformations=(
                "Urgencia + evidencia + estrategia + causalidad → TPI",
            ),
            location="src/territorial/tpi.py",
            caveat="Incluye aforo, importancia y accesibilidad estimados.",
        ),
        LineageRecord(
            datum="Decisión recomendada",
            value=(
                f"Tier {asset.tier} · {action_label}"
                if asset.tier is not None
                else "Sin recomendación"
            ),
            stage="Decisión",
            epistemic_type=DataType.CALCULATED,
            evidence_class=EvidenceClass.CALIBRATED,
            source="Clasificador y asignador territorial SNTO",
            observed_at=None,
            transformations=("TPI + gates EHS/DCS/tendencia → tier y acción",),
            location="src/territorial/tpi.py",
            caveat="Recomendación técnica; no constituye una orden administrativa.",
        ),
    )
    return LineageProfile(
        asset_id=asset.asset_id,
        asset_name=asset.name,
        records=records,
    )


def build_lineage_profiles(
    assets: Sequence[TerritorialAsset],
    calibrations: dict[str, CalibrationResult],
    scene_dates: Sequence[str] = (),
) -> list[LineageProfile]:
    """Build profiles in the ranked asset order supplied by the dashboard."""
    return [
        build_lineage_profile(
            asset,
            calibrations.get(asset.asset_id),
            scene_dates,
        )
        for asset in assets
    ]
