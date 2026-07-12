"""F7 — Audience view profiles (técnica / gestor / tribunal)."""
from __future__ import annotations

import pytest

from src.platform.views import (
    ConfidenceDetail,
    ViewMode,
    get_view,
    view_modes,
)


def test_three_views_in_stable_order():
    modes = view_modes()
    assert modes == [ViewMode.TECNICA, ViewMode.GESTOR, ViewMode.TRIBUNAL]


def test_get_view_accepts_enum_and_string():
    assert get_view(ViewMode.GESTOR).label == "Gestor"
    assert get_view("tribunal").mode is ViewMode.TRIBUNAL


def test_confidence_detail_increases_for_tribunal():
    assert get_view(ViewMode.TECNICA).confidence_detail is ConfidenceDetail.RAW
    assert get_view(ViewMode.GESTOR).confidence_detail is ConfidenceDetail.CONCISE
    assert get_view(ViewMode.TRIBUNAL).confidence_detail is ConfidenceDetail.FULL


def test_every_view_has_renderable_fields():
    for mode in view_modes():
        v = get_view(mode)
        assert v.icon and v.label and v.audience and v.emphasis and v.banner


def test_unknown_view_raises():
    with pytest.raises(ValueError):
        get_view("ejecutiva")


# ── F10 Fase 2: helper único de divulgación por capas ─────────────────────────
def test_section_no_args_is_common_core():
    # Sin requisitos, la sección es núcleo común: visible en las tres vistas.
    for mode in view_modes():
        assert get_view(mode).section() is True


def test_section_simplified_only_gestor():
    assert get_view(ViewMode.GESTOR).section(simplified=True) is True
    assert get_view(ViewMode.TECNICA).section(simplified=True) is False
    assert get_view(ViewMode.TRIBUNAL).section(simplified=True) is False


def test_section_technical_is_tecnica_and_tribunal():
    assert get_view(ViewMode.TECNICA).section(technical=True) is True
    assert get_view(ViewMode.TRIBUNAL).section(technical=True) is True
    assert get_view(ViewMode.GESTOR).section(technical=True) is False


def test_section_audit_only_tribunal():
    assert get_view(ViewMode.TRIBUNAL).section(audit=True) is True
    assert get_view(ViewMode.TECNICA).section(audit=True) is False
    assert get_view(ViewMode.GESTOR).section(audit=True) is False


def test_section_multiple_axes_are_inclusive_or():
    # simplified OR audit → Gestor (simplified) y Auditoría (audit), no Técnica.
    assert get_view(ViewMode.GESTOR).section(simplified=True, audit=True) is True
    assert get_view(ViewMode.TRIBUNAL).section(simplified=True, audit=True) is True
    assert get_view(ViewMode.TECNICA).section(simplified=True, audit=True) is False
