"""UI tests for the temporal GIF section of the Change Explorer tab (ADR-015).

Uses a minimal Streamlit stand-in plus a fake animation service. No Streamlit
runtime, no Earth Engine, no network. The GIF section is exercised directly
(``_render_animation_section``) and through the result path (``_render_result``).
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime, timezone

import src.ui.tabs.tab_change_explorer as tab
from src.analysis.change_detection.models import CompositeKind, DateWindow, WindowRole
from src.analysis.change_detection.quality import evaluate_quality
from src.integrations.earth_engine.errors import EarthEngineQuotaError
from src.services.change_animation_service import (
    AnimatedArtifact,
    AnimationFrameMetadata,
    ChangeAnimationRequest,
    GifTooLargeError,
    InsufficientUsableFramesError,
)
from src.services.change_explorer_service import (
    ChangeExplorerRequest,
    ChangeExplorerResult,
    RenderedArtifact,
    ResultStatus,
)

_SECRET = "SUPER-SECRET-TOKEN"
_GIF = b"GIF89a" + b"\x00" * 64


class _Ctx:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _FakeSt:
    """Records calls; per-form submit; widgets write into session_state."""

    def __init__(self, widget_values: dict, submit_form: str | None = None) -> None:
        self.session_state: dict = {}
        self._widget_values = widget_values
        self._submit_form = submit_form
        self._current_form: str | None = None
        self.markdowns: list[str] = []
        self.captions: list[str] = []
        self.infos: list[str] = []
        self.warnings: list[str] = []
        self.errors: list[str] = []
        self.writes: list = []
        self.images: list = []
        self.downloads: list[dict] = []
        self.spinners: list[str] = []
        self._in_spinner = False

    def subheader(self, *a, **k): pass
    def divider(self, *a, **k): pass
    def markdown(self, msg="", *a, **k): self.markdowns.append(str(msg))
    def caption(self, msg="", *a, **k): self.captions.append(str(msg))
    def info(self, msg="", *a, **k): self.infos.append(str(msg))
    def warning(self, msg="", *a, **k): self.warnings.append(str(msg))
    def error(self, msg="", *a, **k): self.errors.append(str(msg))
    def write(self, obj="", *a, **k): self.writes.append(obj)
    def image(self, obj="", *a, **k): self.images.append((obj, k))

    def download_button(self, label, data=None, file_name=None, mime=None, **k):
        self.downloads.append(
            {"label": label, "data": data, "file_name": file_name, "mime": mime}
        )

    @contextmanager
    def form(self, name="", *a, **k):
        prev = self._current_form
        self._current_form = name
        try:
            yield _Ctx()
        finally:
            self._current_form = prev

    @contextmanager
    def spinner(self, msg="", *a, **k):
        self.spinners.append(str(msg))
        self._in_spinner = True
        try:
            yield _Ctx()
        finally:
            self._in_spinner = False

    @contextmanager
    def expander(self, label="", *a, **k):
        yield _Ctx()

    def columns(self, n, *a, **k):
        return [_Ctx() for _ in range(n if isinstance(n, int) else len(n))]

    def _wv(self, key, default=None):
        return self._widget_values.get(key, default)

    def selectbox(self, label, options=None, key=None, index=0, **k):
        val = self._wv(key, (options[index] if options else None))
        if key:
            self.session_state[key] = val
        return val

    def date_input(self, label, value=None, key=None, **k):
        val = self._wv(key, value)
        if key:
            self.session_state[key] = val
        return val

    def form_submit_button(self, *a, **k):
        return self._current_form == self._submit_form


# ── Fixtures / builders ───────────────────────────────────────────────────────

def _quality(scene=8, valid=800, aoi=1000, window=None):
    return evaluate_quality(
        window=window or DateWindow(date(2023, 7, 1), date(2023, 8, 31)),
        requested_max_cloud_pct=20.0, scene_count=scene, valid_pixel_count=valid,
        aoi_pixel_count=aoi, mean_scene_cloud_pct=12.5,
    )


def _explorer_result(status=ResultStatus.OK, with_artifacts=True):
    before = DateWindow(date(2023, 7, 1), date(2023, 8, 31))
    after = DateWindow(date(2024, 7, 1), date(2024, 8, 31))
    req = ChangeExplorerRequest(
        territory_id="pnsg", product=CompositeKind.NDVI, before=before, after=after,
        max_cloud_pct=20.0, dimensions=512,
    )
    kw = {}
    if with_artifacts:
        def _art(role, product=CompositeKind.NDVI, window=None):
            return RenderedArtifact(
                product=product, role=role, dimensions=512,
                window=window or before, visualization_id="ndvi:vis-v1",
                url=f"https://ee.example/{_SECRET}",
            )
        kw = dict(
            before_artifact=_art(WindowRole.BEFORE, window=before),
            after_artifact=_art(WindowRole.AFTER, window=after),
            dndvi_artifact=_art(WindowRole.DIFFERENCE, product=CompositeKind.DNDVI),
        )
    return ChangeExplorerResult(
        territory_id="pnsg", territory_name="Parque Nacional Sierra de Guadarrama",
        product=CompositeKind.NDVI, status=status, request=req,
        before_quality=_quality(window=before), after_quality=_quality(window=after),
        warnings=(), evidence_label="Observación real Sentinel-2 — no validada.",
        generated_at=datetime(2024, 9, 1, 10, 0, tzinfo=timezone.utc), **kw,
    )


def _artifact():
    req = ChangeAnimationRequest(
        territory_id="pnsg", product=CompositeKind.NDVI, start=date(2023, 7, 1),
        end=date(2024, 8, 31), max_cloud_pct=20.0, dimensions=256,
        max_frame_count=8, frames_per_second=2,
    )
    frames = (
        AnimationFrameMetadata(0, "2023-07-01", "2023-09-30", "2023-10-01", 5,
                               CompositeKind.NDVI),
        AnimationFrameMetadata(1, "2023-10-01", "2023-12-31", "2024-01-01", 4,
                               CompositeKind.NDVI),
    )
    return AnimatedArtifact(
        territory_id="pnsg", territory_name="PNSG", product=CompositeKind.NDVI,
        dimensions=256, frames_per_second=2, frame_count=2, planned_frame_count=2,
        frames=frames, warnings=(), byte_size=len(_GIF),
        generated_at=datetime(2024, 9, 1, 10, 0, tzinfo=timezone.utc),
        request=req, gif_bytes=_GIF,
    )


def _anim_widgets():
    return {
        "ca_start": date(2023, 7, 1),
        "ca_end": date(2024, 8, 31),
        "ca_max_frames": 8,
        "ca_dimensions": 256,
        "ca_fps": 2,
    }


# ── Gating: GIF section only below a successful swipe ─────────────────────────

def test_no_gif_section_when_no_swipe(monkeypatch):
    called = []
    monkeypatch.setattr(
        tab, "cached_run_change_animation", lambda r: called.append(r)
    )
    fake = _FakeSt({}, submit_form=None)
    monkeypatch.setattr(tab, "st", fake)
    tab._render_result(_explorer_result(ResultStatus.NO_DATA, with_artifacts=False))
    assert called == []
    assert not any("Animación temporal" in m for m in fake.markdowns)


def test_gif_section_present_below_swipe(monkeypatch):
    monkeypatch.setattr(tab, "image_comparison", lambda **k: None)
    fake = _FakeSt({}, submit_form=None)
    monkeypatch.setattr(tab, "st", fake)
    tab._render_result(_explorer_result())
    assert any("Animación temporal" in m for m in fake.markdowns)


# ── Explicit trigger: no run before submit ────────────────────────────────────

def test_no_service_call_before_submit(monkeypatch):
    called = []
    monkeypatch.setattr(
        tab, "cached_run_change_animation", lambda r: called.append(r) or _artifact()
    )
    fake = _FakeSt(_anim_widgets(), submit_form=None)  # not submitted
    monkeypatch.setattr(tab, "st", fake)
    tab._render_animation_section(_explorer_result())
    assert called == []
    assert tab.ANIMATION_SESSION_KEY not in fake.session_state


def test_submit_calls_service_once_and_stores(monkeypatch):
    called = []

    def _svc(req):
        called.append(req)
        return _artifact()

    monkeypatch.setattr(tab, "cached_run_change_animation", _svc)
    fake = _FakeSt(_anim_widgets(), submit_form="change_animation_form")
    monkeypatch.setattr(tab, "st", fake)
    tab._render_animation_section(_explorer_result())
    assert len(called) == 1
    assert fake.session_state.get(tab.ANIMATION_SESSION_KEY) is not None


def test_service_runs_inside_spinner(monkeypatch):
    seen = {}

    def _svc(req):
        seen["in_spinner"] = fake._in_spinner
        return _artifact()

    monkeypatch.setattr(tab, "cached_run_change_animation", _svc)
    fake = _FakeSt(_anim_widgets(), submit_form="change_animation_form")
    monkeypatch.setattr(tab, "st", fake)
    tab._render_animation_section(_explorer_result())
    assert fake.spinners and seen["in_spinner"] is True


# ── Rendering: bytes, download, metadata, disclaimer, no URL ──────────────────

def test_gif_rendered_from_bytes_with_download(monkeypatch):
    monkeypatch.setattr(
        tab, "cached_run_change_animation", lambda r: _artifact()
    )
    fake = _FakeSt(_anim_widgets(), submit_form="change_animation_form")
    monkeypatch.setattr(tab, "st", fake)
    tab._render_animation_section(_explorer_result())
    # GIF bytes reached st.image (never a URL).
    assert any(obj == _GIF for obj, _ in fake.images)
    # A download button carries the in-memory bytes and a descriptive filename.
    assert fake.downloads
    dl = fake.downloads[0]
    assert dl["data"] == _GIF
    assert dl["file_name"] == "snto_pnsg_ndvi_2023-07-01_2024-08-31.gif"
    assert dl["mime"] == "image/gif"


def test_disclaimer_and_frame_counts_shown(monkeypatch):
    monkeypatch.setattr(
        tab, "cached_run_change_animation", lambda r: _artifact()
    )
    fake = _FakeSt(_anim_widgets(), submit_form="change_animation_form")
    monkeypatch.setattr(tab, "st", fake)
    tab._render_animation_section(_explorer_result())
    assert any("exploratoria" in c for c in fake.captions)
    assert any("2 usados" in m or "Fotogramas: **2**" in m for m in fake.markdowns)


def test_no_signed_url_text_rendered(monkeypatch):
    monkeypatch.setattr(
        tab, "cached_run_change_animation", lambda r: _artifact()
    )
    fake = _FakeSt(_anim_widgets(), submit_form="change_animation_form")
    monkeypatch.setattr(tab, "st", fake)
    tab._render_animation_section(_explorer_result())
    text = fake.markdowns + fake.captions + fake.errors + [str(w) for w in fake.writes]
    assert not any(_SECRET in t for t in text)


# ── Failure isolation & error mapping ─────────────────────────────────────────

def test_gif_failure_does_not_clear_swipe(monkeypatch):
    def _boom(req):
        raise EarthEngineQuotaError("quota")

    monkeypatch.setattr(tab, "cached_run_change_animation", _boom)
    fake = _FakeSt(_anim_widgets(), submit_form="change_animation_form")
    fake.session_state[tab.SESSION_KEY] = _explorer_result()  # swipe stays
    monkeypatch.setattr(tab, "st", fake)
    tab._render_animation_section(_explorer_result())
    assert tab.SESSION_KEY in fake.session_state  # swipe result untouched
    assert tab.ANIMATION_SESSION_KEY not in fake.session_state
    assert fake.warnings or fake.errors


def test_insufficient_frames_warns(monkeypatch):
    def _boom(req):
        raise InsufficientUsableFramesError("only 1 frame")

    monkeypatch.setattr(tab, "cached_run_change_animation", _boom)
    fake = _FakeSt(_anim_widgets(), submit_form="change_animation_form")
    monkeypatch.setattr(tab, "st", fake)
    tab._render_animation_section(_explorer_result())
    assert any("fotogramas" in w.lower() for w in fake.warnings)


def test_too_large_warns(monkeypatch):
    def _boom(req):
        raise GifTooLargeError("too big")

    monkeypatch.setattr(tab, "cached_run_change_animation", _boom)
    fake = _FakeSt(_anim_widgets(), submit_form="change_animation_form")
    monkeypatch.setattr(tab, "st", fake)
    tab._render_animation_section(_explorer_result())
    assert any("8 MiB" in w for w in fake.warnings)


def test_no_traceback_leaked_on_failure(monkeypatch):
    def _boom(req):
        raise EarthEngineQuotaError("quota")

    monkeypatch.setattr(tab, "cached_run_change_animation", _boom)
    fake = _FakeSt(_anim_widgets(), submit_form="change_animation_form")
    monkeypatch.setattr(tab, "st", fake)
    tab._render_animation_section(_explorer_result())
    surfaced = fake.errors + fake.warnings + fake.captions + fake.markdowns
    assert not any("Traceback" in s for s in surfaced)


# ── Compatibility signature: an incompatible analysis invalidates the old GIF ─

def test_changed_analysis_drops_stale_gif(monkeypatch):
    monkeypatch.setattr(tab, "cached_run_change_animation", lambda r: _artifact())
    fake = _FakeSt(_anim_widgets(), submit_form=None)  # no submit this rerun
    # A stale GIF stored for a DIFFERENT signature.
    fake.session_state[tab.ANIMATION_SESSION_KEY] = _artifact()
    fake.session_state[tab.ANIMATION_SIGNATURE_KEY] = ("other", "signature")
    monkeypatch.setattr(tab, "st", fake)
    tab._render_animation_section(_explorer_result())
    # Signature mismatch drops the stale GIF (not shown / not relabeled).
    assert fake.session_state.get(tab.ANIMATION_SESSION_KEY) is None
