"""RR-Y1-028 (D2) -- annualizing an OVERLAPPING h-day return series.

``harness._returns_cost`` builds its headline active series from
``forward_return(panel, h)`` where ``h = signal.construction_window``. That is an h-day
return sampled on EVERY trading day -- an overlapping series. Its annualizer is 252/h.

The bug: it used ``* 252``, i.e. it treated an h-day return as a 1-day return. At h=21 the
reported gross/net/real/per-regime/plateau were ~21x too large. Costs were NOT inflated
(turnover genuinely is daily), so ``net = gross - cost`` compared two different scales.

The reason it never surfaced: every engine unit test and the committed PEAD Stage-0 run at
``construction_window = 1``, where 252/1 == 252 and the bug is invisible. The one committed
run at h>1 (VIOP-K2, h=21) had a gross signal of ~0, and 21 x 0 is still 0.

These tests pin BOTH halves of the contract:
  1. h=1 is BYTE-IDENTICAL to the pre-fix behaviour (zero regression -- this is a gate).
  2. h>1 no longer scales the annualized figures with h.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.engine import config
from src.engine.contracts import (
    DialConfig,
    Frequency,
    Panel,
    SortDepth,
    SplitMode,
    SplitSpec,
)
from src.engine.harness import _returns_cost


class _ConstSignal:
    """A fixed per-name score vector, identical every date, parameterized only by h.

    The TILT it produces is therefore the same basket at every horizon; only the
    forward-return window changes. So the annualized active return must be (approximately)
    INVARIANT in h -- any residual h-scaling is the D2 bug.
    """

    def __init__(self, h: int, names: list[str]) -> None:
        self.name = f"const_h{h}"
        self.construction_window = int(h)
        self._vec = pd.Series(np.linspace(1.0, 0.0, len(names)), index=names)

    def scores(self, panel: Panel, names: list[str], asof: pd.Timestamp) -> pd.Series:
        return self._vec.reindex(names)


@pytest.fixture(scope="module")
def panel() -> Panel:
    rng = np.random.default_rng(11)
    n_days, n_names = 900, 60
    dates = pd.bdate_range("2020-01-01", periods=n_days)
    names = [f"N{i:02d}" for i in range(n_names)]
    # a persistent cross-sectional drift so the tilt has a non-zero, stable active return
    drift = np.linspace(0.0004, -0.0004, n_names)
    steps = rng.normal(0.0, 0.012, size=(n_days, n_names)) + drift
    px = pd.DataFrame(100.0 * np.exp(np.cumsum(steps, axis=0)), index=dates, columns=names)
    val = pd.DataFrame(5e7, index=dates, columns=names)
    mkt = pd.Series(100.0 * np.exp(np.cumsum(rng.normal(0, 0.008, n_days))), index=dates)
    lvl = pd.Series(np.linspace(100.0, 150.0, n_days), index=dates)
    return Panel(
        close=px, tr_gross=px, tr_net=px, value_tl=val, membership={},
        market=mkt, tufe=lvl, tlref=lvl, frequency=Frequency.DAILY,
    )


@pytest.fixture(scope="module")
def spec() -> SplitSpec:
    return SplitSpec(
        split_mode=SplitMode.NAME,
        frequency=Frequency.DAILY,
        embargo_h=1,
        sort_depth=SortDepth.TERCILE,
    )


def _rc(panel, spec, h):
    return _returns_cost(panel, _ConstSignal(h, panel.names), spec, DialConfig())


class TestZeroRegressionAtH1:
    """GATE: at h=1 the corrected annualizer (252/1) IS the old one (252). Byte-identical."""

    def test_h1_annualizer_is_exactly_252(self, panel, spec):
        rc = _rc(panel, spec, 1)
        expected = float(rc.active.mean() * config.TRADING_DAYS_YR)
        assert rc.gross_active_ann == pytest.approx(expected, rel=0, abs=0)

    def test_h1_nw_lag_is_still_the_daily_default(self, panel, spec):
        """h=1 must not silently widen the HAC bandwidth."""
        assert DialConfig().nw_lag_for(Frequency.DAILY, h=1) == config.NW_LAG_DAILY


class TestAnnualizationIsHorizonCorrect:
    def test_gross_does_not_scale_with_h(self, panel, spec):
        """THE regression. Pre-fix these differed by a factor of ~h."""
        g1 = _rc(panel, spec, 1).gross_active_ann
        g21 = _rc(panel, spec, 21).gross_active_ann
        assert np.isfinite(g1) and np.isfinite(g21)
        # same basket, same drift -> same annualized active, within sampling noise.
        # Pre-fix this ratio was ~21.
        assert abs(g21 / g1) < 3.0, f"gross still scales with h (g1={g1}, g21={g21})"

    @pytest.mark.parametrize("h", [1, 5, 21])
    def test_annualizer_equals_252_over_h(self, panel, spec, h):
        rc = _rc(panel, spec, h)
        expected = float(rc.active.mean() * (config.TRADING_DAYS_YR / h))
        assert rc.gross_active_ann == pytest.approx(expected, rel=1e-12)

    def test_cost_annualizer_is_unchanged(self, panel, spec):
        """Cost is NOT h-scaled: turnover really is daily. Only the RETURN leg was wrong."""
        rc1, rc21 = _rc(panel, spec, 1), _rc(panel, spec, 21)
        assert np.isfinite(rc1.cost_ann) and np.isfinite(rc21.cost_ann)
        # both annualize turnover over 252 trading days; they must be the same order
        assert rc21.cost_ann == pytest.approx(rc1.cost_ann, rel=0.5)


class TestNWLagCoversTheOverlap:
    def test_lag_widens_to_h_when_overlapping(self):
        """A 21-day overlapping series needs a HAC bandwidth >= 21; the default was 5."""
        d = DialConfig()
        assert d.nw_lag_for(Frequency.DAILY, h=21) >= 21
        assert d.nw_lag_for(Frequency.DAILY, h=5) >= config.NW_LAG_DAILY

    def test_explicit_nw_lag_still_wins(self):
        """An operator-set lag is not overridden by the h-aware default."""
        assert DialConfig(nw_lag=7).nw_lag_for(Frequency.DAILY, h=21) == 7

    def test_default_signature_is_backward_compatible(self):
        """Existing callers pass frequency only (moda/modb/modc) -- must keep working."""
        assert DialConfig().nw_lag_for(Frequency.DAILY) == config.NW_LAG_DAILY
        assert DialConfig().nw_lag_for(Frequency.MONTHLY) == config.NW_LAG_MONTHLY
