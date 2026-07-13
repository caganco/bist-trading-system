"""Tier-A tests for the real-return deflate + benchmark-floor (math-spec Section 6/7).

Pins the four frozen rules:
1. real-return is ALWAYS TUFE-deflated (CPI finite from 2019);
2. the floor is TUFE-only before 2022-07 (no guard -- by design);
3. the floor is max(TUFE, TLREF) once both are eligible (2022-07+);
4. the d213 silent-NaN trap: a window that straddles -- or reaches a non-finite
   TLREF inside -- the eligible region must guard-RAISE and fall back to TUFE-only,
   never let a silent NaN collapse the max.

The level-series are built so a month-start-to-month-start window has an exact,
hand-derivable calendar-day CAGR (a 1.5x/yr TUFE level => 0.5 annualized), so the
asserts pin the asof-lookup + the 365.25 CAGR wiring, not a tautology.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.engine.benchmark import BenchmarkFloor, benchmark_floor
from src.engine.contracts import Frequency, Panel

_MS = pd.date_range("2019-01-01", "2026-05-01", freq="MS")
_TUFE_START = pd.Timestamp("2019-01-01")


def _levels(annual_factor: float, *, start: pd.Timestamp = _TUFE_START) -> pd.Series:
    """LEVEL series whose calendar-day CAGR between any two index points is exactly
    ``annual_factor - 1`` (level = factor ** (calendar-days-from-start / 365.25))."""
    years = (_MS - start).days / 365.25
    return pd.Series(annual_factor**years, index=_MS)


def _tlref(annual_factor: float, *, finite_from: str) -> pd.Series:
    """TLREF-like LEVEL series: NaN before ``finite_from`` (the silent-NaN region),
    then a clean ``annual_factor`` CAGR level afterwards."""
    start = pd.Timestamp(finite_from)
    years = (_MS - start).days / 365.25
    vals = np.where(_MS >= start, annual_factor**years, np.nan)
    return pd.Series(vals, index=_MS)


def _panel(tufe: pd.Series, tlref: pd.Series) -> Panel:
    """Minimal Panel -- benchmark_floor reads only ``tufe`` / ``tlref``."""
    idx = pd.bdate_range("2019-01-02", periods=4)
    frame = pd.DataFrame(1.0, index=idx, columns=["A"])
    one = pd.Series(1.0, index=idx)
    return Panel(
        close=frame, tr_gross=frame, tr_net=frame, value_tl=frame,
        membership={}, market=one, tufe=tufe, tlref=tlref, frequency=Frequency.DAILY,
    )


def _default_panel() -> Panel:
    return _panel(_levels(1.5), _tlref(1.2, finite_from="2022-07-01"))


def test_tufe_only_pre_2022_07_no_guard():
    d0, d1 = pd.Timestamp("2020-01-01"), pd.Timestamp("2021-01-01")
    bf = benchmark_floor(0.8, _default_panel(), d0, d1)
    assert isinstance(bf, BenchmarkFloor)
    assert bf.tlref_ann is None                       # window predates clean TLREF
    assert bf.guard_raised is False and bf.guard_messages == ()  # by design, no guard
    assert bf.tufe_ann == pytest.approx(0.5)
    assert bf.benchmark_floor_ann == pytest.approx(0.5)
    # D3: the deflated quantity is now the TOTAL return, not a spread.
    assert bf.real_total_ann == pytest.approx(1.8 / 1.5 - 1.0)  # (1+total)/(1+tufe)-1


def test_straddle_window_raises_guard_and_falls_back_to_tufe():
    d0, d1 = pd.Timestamp("2022-01-01"), pd.Timestamp("2023-01-01")  # crosses 2022-07
    bf = benchmark_floor(0.8, _default_panel(), d0, d1)
    assert bf.tlref_ann is None
    assert bf.guard_raised is True
    assert any("straddle" in m for m in bf.guard_messages)
    assert bf.benchmark_floor_ann == pytest.approx(bf.tufe_ann)  # TUFE-only fallback


def test_post_window_floor_is_max_tufe_tlref():
    d0, d1 = pd.Timestamp("2022-08-01"), pd.Timestamp("2023-08-01")  # both eligible
    bf = benchmark_floor(0.8, _default_panel(), d0, d1)
    assert bf.guard_raised is False
    assert bf.tufe_ann == pytest.approx(0.5)
    assert bf.tlref_ann == pytest.approx(0.2)
    assert bf.benchmark_floor_ann == pytest.approx(0.5)  # max(0.5, 0.2)


def test_tlref_can_be_the_binding_floor():
    # TUFE 10%/yr, TLREF 40%/yr post-2022-07 -> the floor must pick TLREF.
    panel = _panel(_levels(1.1), _tlref(1.4, finite_from="2022-07-01"))
    bf = benchmark_floor(0.8, panel, pd.Timestamp("2022-08-01"), pd.Timestamp("2023-08-01"))
    assert bf.tlref_ann == pytest.approx(0.4)
    assert bf.benchmark_floor_ann == pytest.approx(0.4)  # max(0.1, 0.4) = TLREF
    assert bf.benchmark_floor_ann > bf.tufe_ann


def test_nonfinite_tlref_inside_eligible_window_guards_and_falls_back():
    # TLREF clean only from 2023-01; a 2022-08..2022-12 window is past tlref_from
    # (2022-07) yet hits the silent NaN -> guard-RAISE, TUFE-only fallback.
    panel = _panel(_levels(1.5), _tlref(1.2, finite_from="2023-01-01"))
    bf = benchmark_floor(0.8, panel, pd.Timestamp("2022-08-01"), pd.Timestamp("2022-12-01"))
    assert bf.tlref_ann is None
    assert bf.guard_raised is True
    assert any("non-finite" in m for m in bf.guard_messages)
    assert bf.benchmark_floor_ann == pytest.approx(bf.tufe_ann)


def test_tufe_unavailable_makes_real_and_beats_undefined():
    nan_tufe = pd.Series(np.nan, index=_MS)
    panel = _panel(nan_tufe, _tlref(1.2, finite_from="2022-07-01"))
    bf = benchmark_floor(0.8, panel, pd.Timestamp("2020-01-01"), pd.Timestamp("2021-01-01"))
    assert np.isnan(bf.tufe_ann)
    assert np.isnan(bf.real_total_ann)
    assert np.isnan(bf.benchmark_floor_ann)
    assert bf.beats_benchmark_floor is None
    assert any("TUFE" in m for m in bf.guard_messages)


@pytest.mark.parametrize(
    ("nominal_total", "expected_beats"),
    [
        (1.4, True),   # 140% nominal total vs a 50% floor -> beats
        (0.8, True),   # 80%  nominal total vs a 50% floor -> beats
        (0.3, False),  # 30%  nominal total vs a 50% floor -> does NOT beat
        (0.0, False),  # flat nominal -> does NOT beat
    ],
    # (no "exactly at the floor" row: the floor is a CAGR carrying float noise
    #  (0.4999999999999998), so an equality-boundary case would test float dust, not behaviour.)
)
def test_beats_benchmark_floor_both_directions(nominal_total, expected_beats):
    """D3: like against like -- nominal TOTAL vs the nominal floor.

    The (0.8, ...) row is the regression. Pre-RR-Y1-028 an 80%-nominal strategy against a
    50% inflation floor was recorded as FAILING, because the code deflated the input
    (0.8 -> 0.2 real) and then compared that REAL number to the NOMINAL 0.5 floor.
    """
    bf = benchmark_floor(
        nominal_total, _default_panel(), pd.Timestamp("2020-01-01"), pd.Timestamp("2021-01-01")
    )
    assert bf.beats_benchmark_floor is expected_beats


def test_real_vs_real_agrees_with_nominal_vs_nominal():
    """D3: deflating both sides by the same TUFE is monotone -> identical boolean.

    This is the invariant the old code broke by deflating ONE side only.
    """
    for nominal_total in (0.2, 0.5, 0.8, 1.4):
        bf = benchmark_floor(
            nominal_total, _default_panel(),
            pd.Timestamp("2020-01-01"), pd.Timestamp("2021-01-01"),
        )
        real_beats = bf.real_total_ann > bf.benchmark_floor_real_ann
        assert real_beats is bf.beats_benchmark_floor


def test_real_active_ann_is_retained_but_descriptive():
    """D3 strangler: the committed field survives and keeps its old meaning (a deflated
    SPREAD) -- it is simply no longer the quantity the gate judges."""
    bf = benchmark_floor(
        0.8, _default_panel(), pd.Timestamp("2020-01-01"), pd.Timestamp("2021-01-01"),
        nominal_active_ann=0.05,
    )
    assert bf.real_active_ann == pytest.approx(1.05 / 1.5 - 1.0)
    # ... and it is NOT what decided the verdict: the spread deflates to a NEGATIVE number,
    # yet the strategy (80% nominal total) still beats the 50% floor.
    assert bf.real_active_ann < 0
    assert bf.beats_benchmark_floor is True


def test_a_healthy_tilt_in_a_high_inflation_window_is_no_longer_auto_failed():
    """D3 sanity (the directive's named case): a +5%/yr tilt on top of an EW benchmark
    that itself returned 60% nominal, in a 50%-inflation window, must PASS."""
    bench_ann, net_active_ann = 0.60, 0.05
    bf = benchmark_floor(
        bench_ann + net_active_ann, _default_panel(),
        pd.Timestamp("2020-01-01"), pd.Timestamp("2021-01-01"),
        nominal_active_ann=net_active_ann,
    )
    assert bf.benchmark_floor_ann == pytest.approx(0.5)
    assert bf.beats_benchmark_floor is True          # 0.65 > 0.50
    assert bf.real_total_ann == pytest.approx(1.65 / 1.5 - 1.0)


def test_cagr_matches_independent_hand_computation():
    # Re-derive the floor's TUFE CAGR from the raw asof-levels + the 365.25 constant
    # (independent of benchmark.py's internals) -> pins the asof + formula wiring.
    panel = _default_panel()
    d0, d1 = pd.Timestamp("2020-01-01"), pd.Timestamp("2022-01-01")
    lvl0 = float(panel.tufe.asof(d0))
    lvl1 = float(panel.tufe.asof(d1))
    days = (d1 - d0).days
    expected = (lvl1 / lvl0) ** (365.25 / days) - 1.0
    bf = benchmark_floor(0.0, panel, d0, d1)
    assert bf.tufe_ann == pytest.approx(expected)
