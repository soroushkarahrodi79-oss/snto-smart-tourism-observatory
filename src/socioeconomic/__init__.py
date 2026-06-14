"""
SNTO — Socioeconomic layer (F9)
================================
Municipal socioeconomic context for the territory, sourced from INE (padrón,
EOATR) and ALMUDENA (Comunidad de Madrid statistical bank), joined to the
observatory's environmental risk by municipality.

The layer is deliberately decoupled from ``TerritorialAsset``: the natural grain
for population/economy is the *municipality*, not the asset. Assets link to a
municipality via :func:`src.socioeconomic.mapping.region_to_ine`.

Public surface:
  - models.Municipality            — one municipality + its indicators + provenance
  - loader.load_municipalities     — read the curated snapshot
  - indicators.compute_svi         — Socioeconomic Vulnerability Index
  - indicators.community_impact    — environmental risk × economic dependence
"""
from __future__ import annotations

from .models import DataCompleteness, Municipality

__all__ = ["Municipality", "DataCompleteness"]
