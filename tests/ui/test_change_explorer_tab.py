"""UI tests for the Change Explorer tab (ADR-015).

Uses a minimal Streamlit stand-in (the repo's `_FakeSt` convention) plus a fake
service. No Streamlit runtime and no Earth Engine contact.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime, timezone

import pytest

import src.ui.tabs.tab_change_explorer as tab
from src.analysis.change_detection.models import CompositeKind, DateWindow, WindowRole
from src.analysis.change_detection.quality import evaluate_quality
from src.integrations.earth_engine.errors import (
    EarthEngineAuthError,
    EarthEngineConfigError,
    EarthEngineDisabledError,
    EarthEngineError,
    EarthEngineQuotaError,
    EarthEngineUnavailableError,
)
from src.services.change_explorer_service import (
    ChangeExplorerRequest,
    ChangeExplorerResult,
    RenderedArtifact,
    ResultStatus,
)

_SECRET_URL = "https://ee.example/thumb/SUPER-SECRET-TOKEN"


class _Ctx:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _FakeSt:
    """Records the calls the tab makes; widgets write into session_state."""

    def __init__(self, widget_values: dict, submit: bool) -> None:
        self.session_state: dict = {}
        self._widget_values = widget_values
        self._submit = submit
        self.infos: list[str] = []
        self.warnings: list[str] = []
        self.errors: list[str] = []
        self.markdowns: list[str] = []
        self.captions: list[str] = []
        self.writes: list = []
        self.images: list = []

    # passthrough / no-op display
    def subheader(self, *a, **k): pass
    def divider(self, *a, **k): pass
    def markdown(self, msg="", *a, **k): self.markdowns.append(str(msg))
    def caption(self, msg="", *a, **k): self.captions.append(str(msg))
    def info(self, msg="", *a, **k): self.infos.append(str(msg))
    def warning(self, msg="", *a, **k): self.warnings.append(str(msg))
    def error(self, msg="", *a, **k): self.errors.append(str(msg))
    def write(self, obj="", *a, **k): self.writes.append(obj)
    def image(self, obj="", *a, **k): self.images.append((obj, k))

    # layout
    @contextmanager
    def form(self, *a, **k):
        yield _Ctx()

    def columns(self, n, *a, **k):
        return [_Ctx() for _ in range(n if isinstance(n, int) else len(n))]

    # widgets: write value into session_state under `key`, return it
    def _wv(self, key, default=None):
        return self._widget_values.get(key, default)

    def selectbox(self, label, options=None, key=None, index=0, **k):
        val = self._wv(key, (options[index] if options else None))
        if key:
            self.session_state[key] = val
        return val

    def radio(self, label, options=None, key=None, index=0, **k):
        val = self._wv(key, (options[index] if options else None))
        if key:
            self.session_state[key] = val
        return val

    def date_input(self, label, value=None, key=None, **k):
        val = self._wv(key, value)
        if key:
            self.session_state[key] = val
        return val

    def slider(self, label, min_value=0, max_value=100, value=0, key=None, **k):
        val = self._wv(key, value)
        if key:
            self.session_state[key] = val
        return val

    def form_submit_button(self, *a, **k):
        return self._submit


def _quality(scene=8, valid=800, aoi=1000, window=None):
    return evaluate_quality(
        window=window or DateWindow(date(2023, 7, 1), date(2023, 8, 31)),
        requested_max_cloud_pct=20.0, scene_count=scene, valid_pixel_count=valid,
        aoi_pixel_count=aoi, mean_scene_cloud_pct=12.5,
    )


def _artifact(role, url=_SECRET_URL, product=CompositeKind.NDVI, window=None):
    return RenderedArtifact(
        product=product, role=role, dimensions=512,
        window=window or DateWindow(date(2023, 7, 1), date(2023, 8, 31)),
        visualization_id="ndvi:vis-v1", url=url,
    )


def _result(status=ResultStatus.OK, with_artifacts=True, before=None, after=None):
    before = before or DateWindow(date(2023, 7, 1), date(2023, 8, 31))
    after = after or DateWindow(date(2024, 7, 1), date(2024, 8, 31))
    req = ChangeExplorerRequest(
        territory_id="pnsg", product=CompositeKind.NDVI, before=before, after=after,
        max_cloud_pct=20.0, dimensions=512,
    )
    kw = {}
    if with_artifacts:
        kw = dict(
            before_artifact=_artifact(WindowRole.BEFORE, window=before),
            after_artifact=_artifact(WindowRole.AFTER, window=after),
            dndvi_artifact=_artifact(
                WindowRole.DIFFERENCE, product=CompositeKind.DNDVI
            ),
        )
    return ChangeExplorerResult(
        territory_id="pnsg", territory_name="Parque Nacional Sierra de Guadarrama",
        product=CompositeKind.NDVI, status=status, request=req,
        before_quality=_quality(window=before), after_quality=_quality(window=after),
        warnings=(),
        evidence_label="Observación real Sentinel-2 — no validada en campo.",
        generated_at=datetime(2024, 9, 1, 10, 0, tzinfo=timezone.utc), **kw,
    )


@pytest.fixture
def enabled(monkeypatch):
    monkeypatch.setattr(
        tab, "settings",
        type("S", (), {"snto_enable_change_explorer": True})(),
    )
    monkeypatch.setattr(tab, "usable_territories", lambda: [("pnsg", "PNSG")])
    calls = {"image_comparison": [], "service": []}
    monkeypatch.setattr(
        tab, "image_comparison",
        lambda **k: calls["image_comparison"].append(k),
    )
    return calls


def _default_widgets():
    return {
        "ce_territory": "pnsg",
        "ce_product": CompositeKind.NDVI,
        "ce_before_start": date(2023, 7, 1),
        "ce_before_end": date(2023, 8, 31),
        "ce_after_start": date(2024, 7, 1),
        "ce_after_end": date(2024, 8, 31),
        "ce_cloud": 20,
        "ce_dimensions": 512,
    }


def _run(monkeypatch, fake, service_fn=None):
    if service_fn is not None:
        monkeypatch.setattr(tab, "cached_run_change_explorer", service_fn)
    monkeypatch.setattr(tab, "st", fake)
    tab.render_tab_change_explorer()


# ── Feature flag ──────────────────────────────────────────────────────────────

def test_disabled_shows_info_and_no_service(monkeypatch):
    monkeypatch.setattr(
        tab, "settings",
        type("S", (), {"snto_enable_change_explorer": False})(),
    )
    called = []
    monkeypatch.setattr(tab, "cached_run_change_explorer", lambda r: called.append(r))
    fake = _FakeSt(_default_widgets(), submit=False)
    _run(monkeypatch, fake)
    assert any("desactivado" in m for m in fake.infos)
    assert called == []


# ── Form / submit gating ──────────────────────────────────────────────────────

def test_no_service_call_before_submit(monkeypatch, enabled):
    service = []
    fake = _FakeSt(_default_widgets(), submit=False)
    _run(monkeypatch, fake, service_fn=lambda r: service.append(r) or _result())
    assert service == []


def test_valid_submit_calls_service_once(monkeypatch, enabled):
    service = []

    def _svc(req):
        service.append(req)
        return _result()

    fake = _FakeSt(_default_widgets(), submit=True)
    _run(monkeypatch, fake, service_fn=_svc)
    assert len(service) == 1
    assert fake.session_state.get(tab.SESSION_KEY) is not None


def test_invalid_dates_block_service_call(monkeypatch, enabled):
    service = []
    widgets = _default_widgets()
    widgets["ce_before_start"] = date(2023, 8, 31)
    widgets["ce_before_end"] = date(2023, 7, 1)  # reversed -> DateWindow raises
    fake = _FakeSt(widgets, submit=True)
    _run(monkeypatch, fake, service_fn=lambda r: service.append(r))
    assert service == []
    assert fake.errors  # a validation error was surfaced
    assert tab.SESSION_KEY not in fake.session_state


# ── Result rendering ──────────────────────────────────────────────────────────

def test_swipe_receives_urls_and_labels(monkeypatch, enabled):
    fake = _FakeSt(_default_widgets(), submit=True)
    _run(monkeypatch, fake, service_fn=lambda r: _result())
    assert len(enabled["image_comparison"]) == 1
    ic = enabled["image_comparison"][0]
    assert ic["img1"] == _SECRET_URL and ic["img2"] == _SECRET_URL
    assert "2023-07-01" in ic["label1"] and "2024-07-01" in ic["label2"]
    assert ic.get("in_memory") is True


def test_dndvi_and_legend_shown(monkeypatch, enabled):
    fake = _FakeSt(_default_widgets(), submit=True)
    _run(monkeypatch, fake, service_fn=lambda r: _result())
    assert any(url == _SECRET_URL for url, _ in fake.images)
    assert any("dNDVI" in m for m in fake.markdowns)
    assert any("observacional" in c.lower() for c in fake.captions)


def test_quality_metrics_shown_distinctly(monkeypatch, enabled):
    fake = _FakeSt(_default_widgets(), submit=True)
    _run(monkeypatch, fake, service_fn=lambda r: _result())
    keys = set()
    for obj in fake.writes:
        if isinstance(obj, dict):
            keys.update(obj.keys())
    assert any("Nubosidad media de escena" in k for k in keys)
    assert any("píxeles válidos en AOI" in k for k in keys)


def test_evidence_disclaimer_present(monkeypatch, enabled):
    fake = _FakeSt(_default_widgets(), submit=True)
    _run(monkeypatch, fake, service_fn=lambda r: _result())
    assert any("no validada en campo" in c for c in fake.captions)


def test_no_data_status_skips_swipe(monkeypatch, enabled):
    fake = _FakeSt(_default_widgets(), submit=True)
    _run(
        monkeypatch, fake,
        service_fn=lambda r: _result(ResultStatus.NO_DATA, with_artifacts=False),
    )
    assert enabled["image_comparison"] == []
    assert any("datos suficientes" in w for w in fake.warnings)


# ── Error mapping ─────────────────────────────────────────────────────────────

def test_service_error_mapped_to_safe_message(monkeypatch, enabled):
    def _boom(req):
        raise EarthEngineQuotaError("quota exceeded")

    fake = _FakeSt(_default_widgets(), submit=True)
    _run(monkeypatch, fake, service_fn=_boom)
    assert any("cuota" in w.lower() or "límite" in w.lower() for w in fake.warnings)
    assert tab.SESSION_KEY not in fake.session_state  # no stale result
    # No stack-trace / exception text leaked
    assert not any("Traceback" in m for m in fake.markdowns + fake.captions)


@pytest.mark.parametrize(
    "exc",
    [
        EarthEngineDisabledError("off"),
        EarthEngineConfigError("no project"),
        EarthEngineAuthError("permission"),
        EarthEngineUnavailableError("down"),
        EarthEngineError("generic"),
    ],
)
def test_all_ee_errors_are_handled_safely(monkeypatch, enabled, exc):
    def _boom(req):
        raise exc

    fake = _FakeSt(_default_widgets(), submit=True)
    _run(monkeypatch, fake, service_fn=_boom)
    # Every EE failure yields a user-facing message (error/warning/info), never a
    # stale result and never a raw traceback / credential leak.
    surfaced = fake.errors + fake.warnings + fake.infos
    assert surfaced, f"no safe message surfaced for {type(exc).__name__}"
    assert tab.SESSION_KEY not in fake.session_state
    assert not any("Traceback" in m for m in surfaced)


# ── Stale-result safety ───────────────────────────────────────────────────────

def test_old_result_not_relabeled_after_unsent_changes(monkeypatch, enabled):
    # A stored result for one window pair; user changes widgets but does NOT submit.
    stored = _result(
        before=DateWindow(date(2022, 7, 1), date(2022, 8, 31)),
        after=DateWindow(date(2023, 7, 1), date(2023, 8, 31)),
    )
    widgets = _default_widgets()  # different (2023/2024) windows, unsent
    fake = _FakeSt(widgets, submit=False)
    fake.session_state[tab.SESSION_KEY] = stored
    service = []
    _run(monkeypatch, fake, service_fn=lambda r: service.append(r) or _result())
    # No new run; header reflects the STORED result's windows, not the widgets.
    assert service == []
    assert any("2022-07-01" in m for m in fake.markdowns)
    assert not any("2024-07-01" in m for m in fake.markdowns)


# ── No secret leakage ─────────────────────────────────────────────────────────

def test_no_signed_url_text_rendered(monkeypatch, enabled):
    fake = _FakeSt(_default_widgets(), submit=True)
    _run(monkeypatch, fake, service_fn=lambda r: _result())
    # The URL may reach st.image / the swipe component, but must never be written
    # as user-facing text (markdown/caption/write/error).
    text_blobs = (
        fake.markdowns + fake.captions + fake.errors
        + [str(w) for w in fake.writes]
    )
    assert not any("SUPER-SECRET-TOKEN" in t for t in text_blobs)
