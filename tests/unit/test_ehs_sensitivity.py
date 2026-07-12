"""Tests del análisis de sensibilidad del EHS (Morris radial).

Cubren ``src/calibration/ehs_sensitivity.py``.
"""
from __future__ import annotations

import numpy as np

from src.calibration.ehs_sensitivity import (
    ehs_driver_sensitivity,
    morris_radial,
)

# ── morris_radial: propiedades sobre modelos conocidos ──────────────────────────

def test_morris_ranks_linear_coefficients():
    # f = 1*x0 + 5*x1 + 0.1*x2 → influencia x1 > x0 > x2, y additivo (σ≈0).
    def model(u):
        return 1.0 * u[0] + 5.0 * u[1] + 0.1 * u[2]

    r = morris_radial(model, ["x0", "x1", "x2"], n_base=200, seed=1)
    ranked = [name for name, _ in r.ranked()]
    assert ranked == ["x1", "x0", "x2"]
    # modelo aditivo → interacción/no-linealidad ~ 0
    assert max(r.sigma) < 1e-6


def test_morris_direction_sign():
    def model(u):
        return u[0] - u[1]

    r = morris_radial(model, ["up", "down"], n_base=150, seed=2)
    i_up, i_down = r.names.index("up"), r.names.index("down")
    assert r.mu[i_up] > 0
    assert r.mu[i_down] < 0


def test_morris_detects_interaction():
    # f = x0 * x1 → efecto de cada uno depende del otro → σ > 0.
    def model(u):
        return u[0] * u[1]

    r = morris_radial(model, ["a", "b"], n_base=300, seed=3)
    assert min(r.sigma) > 0.05


def test_morris_reproducible_with_seed():
    def model(u):
        return float(np.sum(u ** 2))

    a = morris_radial(model, ["x", "y", "z"], n_base=100, seed=7)
    b = morris_radial(model, ["x", "y", "z"], n_base=100, seed=7)
    assert a.mu_star == b.mu_star


# ── ehs_driver_sensitivity: sobre el modelo EHS real ────────────────────────────

def test_ehs_sensitivity_shape_and_finiteness():
    r = ehs_driver_sensitivity(n_base=120, seed=0)
    assert len(r.names) == 6
    assert all(np.isfinite(v) for v in r.mu_star)
    assert all(v >= 0 for v in r.mu_star)


def test_ehs_more_ndvi_raises_score():
    # Más NDVI base ⇒ menor riesgo base ⇒ mayor EHS: dirección positiva.
    r = ehs_driver_sensitivity(n_base=150, seed=0)
    i = r.names.index("mean_ndvi")
    assert r.mu[i] > 0


def test_ehs_more_anomaly_lowers_score():
    r = ehs_driver_sensitivity(n_base=150, seed=0)
    i = r.names.index("anomaly_frac")
    assert r.mu[i] < 0


def test_ehs_influential_drivers_dominate_negligible():
    # Los drivers con peso alto (base/anomalía) deben influir más que la
    # recuperación, cuyo peso es 0.10 y opera en un rango estrecho.
    r = ehs_driver_sensitivity(n_base=200, seed=0)
    d = dict(zip(r.names, r.mu_star))
    assert d["mean_ndvi"] > d["recovery_frac"]
    assert d["anomaly_frac"] > d["recovery_frac"]
