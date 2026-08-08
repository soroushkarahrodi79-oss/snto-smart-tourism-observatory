"""UI evidence-gate tests (Phase 0.5E · I-5).

Prove the two direct-UI bypasses honour the machine-readable evidence class:
  * the KPI tab does not present a synthetic portfolio's first asset as an
    authorized "Acción prioritaria del territorio"; and
  * the reports tab does not offer the executive brief as an authorized download
    for a synthetic portfolio.

They follow the repo's fake-Streamlit pattern (see
``tests/ui/test_urgent_actions_tab_unit.py``) and stub the heavy downstream
render helpers so only the gated behaviour is exercised.
"""
from __future__ import annotations

import src.ui.tabs.tab_kpis as kpis_tab
import src.ui.tabs.tab_reports as reports_tab
from src.platform.evidence import EvidenceClass
from src.territorial.models import AssetType, TerritorialAsset


def _asset(asset_id: str, evidence_class: EvidenceClass) -> TerritorialAsset:
    return TerritorialAsset(
        asset_id=asset_id, name="Laguna de prueba", asset_type=AssetType.TRAIL,
        region="Rascafría", ehs=35.0, risk_score=0.77, dcs=79.0,
        alert_level="CRITICAL_INTERVENTION", scm_classification="LOCALIZED_IMPACT",
        scm_confidence="HIGH", trend_direction="decreasing", mk_p_value=0.006,
        visitor_capacity_annual=120_000, economic_importance=0.9,
        accessibility_score=0.9, tier=1,
        recommended_action_label="Inspección urgente",
        evidence_class=evidence_class,
    )


class _FakeExpander:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _FakeSt:
    """Records the calls the gate cares about; no-ops everything else."""

    def __init__(self) -> None:
        self.markdowns: list[str] = []
        self.warnings: list[str] = []
        self.infos: list[str] = []
        self.downloads: list[str] = []
        self.session_state: dict = {}

    def subheader(self, *_a, **_k) -> None:
        pass

    def caption(self, *_a, **_k) -> None:
        pass

    def divider(self, *_a, **_k) -> None:
        pass

    def markdown(self, body: str = "", *_a, **_k) -> None:
        self.markdowns.append(body)

    def warning(self, msg: str = "", *_a, **_k) -> None:
        self.warnings.append(msg)

    def info(self, msg: str = "", *_a, **_k) -> None:
        self.infos.append(msg)

    def button(self, *_a, **_k) -> bool:
        return False

    def download_button(self, label: str = "", *_a, **_k) -> None:
        self.downloads.append(label)

    def expander(self, *_a, **_k) -> _FakeExpander:
        return _FakeExpander()


class _FakeView:
    def section(self, *_a, **_k) -> bool:
        return True  # enter the GESTOR priority block / expand previews


# ── KPI tab ──────────────────────────────────────────────────────────────────

def _run_kpi_tab(monkeypatch, assets):
    fake = _FakeSt()
    monkeypatch.setattr(kpis_tab, "st", fake)
    monkeypatch.setattr(kpis_tab, "decision_kpis", lambda _k: [])
    monkeypatch.setattr(kpis_tab, "render_kpi_grid", lambda *a, **k: None)
    monkeypatch.setattr(kpis_tab, "_render_fichas_rapidas", lambda *a, **k: None)
    monkeypatch.setattr(
        kpis_tab,
        "enrichment_summary",
        lambda _c: {"overridden": 0, "total": len(assets)},
    )
    dashboard = type("D", (), {"kpis": []})()
    kpis_tab.render_tab_kpis(dashboard, assets, [], {}, _FakeView())
    return fake


def test_kpi_tab_synthetic_portfolio_gated(monkeypatch) -> None:
    fake = _run_kpi_tab(monkeypatch, [_asset("s1", EvidenceClass.SYNTHETIC)])
    blob = " || ".join(fake.markdowns)
    # The authorized priority block is withheld ...
    assert "Acción prioritaria del territorio" not in blob
    # ... replaced by an explicit synthetic-demo block, plus a warning notice.
    assert "Demostración sintética" in blob
    assert any("sintética de demostración" in w.lower() for w in fake.warnings)


def test_kpi_tab_real_portfolio_shows_authorized_action(monkeypatch) -> None:
    fake = _run_kpi_tab(monkeypatch, [_asset("r1", EvidenceClass.REAL)])
    blob = " || ".join(fake.markdowns)
    assert "Acción prioritaria del territorio" in blob
    assert fake.warnings == []  # no synthetic warning for a REAL portfolio


# ── Reports tab ──────────────────────────────────────────────────────────────

def _run_reports_tab(monkeypatch, assets):
    fake = _FakeSt()
    monkeypatch.setattr(reports_tab, "st", fake)
    # Sections 2-4 use separate real-evidence pipelines; stub them out so only
    # the section-1 download gate is exercised.
    monkeypatch.setattr(reports_tab, "_render_gis_section", lambda *a, **k: None)
    monkeypatch.setattr(reports_tab, "_render_cets_section", lambda *a, **k: None)
    monkeypatch.setattr(reports_tab, "_render_prug_section", lambda *a, **k: None)
    reports_tab.render_tab_reports(
        assets, "pnsg", "PNSG", "2026-08-08", _FakeView()
    )
    return fake


def test_reports_tab_synthetic_portfolio_withholds_download(monkeypatch) -> None:
    fake = _run_reports_tab(monkeypatch, [_asset("s1", EvidenceClass.SYNTHETIC)])
    # No executive-brief download offered; a synthetic warning is shown instead.
    assert fake.downloads == []
    assert any(
        "sintética" in w.lower() or "no publicar" in w.lower() for w in fake.warnings
    )


def test_reports_tab_real_portfolio_offers_download(monkeypatch) -> None:
    fake = _run_reports_tab(monkeypatch, [_asset("r1", EvidenceClass.REAL)])
    # Both .md and .json executive-brief downloads are offered.
    assert len(fake.downloads) == 2
    assert any(".md" in d or "md" in d.lower() for d in fake.downloads)
