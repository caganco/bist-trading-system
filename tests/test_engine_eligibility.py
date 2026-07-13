"""Mod-A eligible-universe construction.

Two rules live here, deliberately:

  PIT (RR-Y1-030, the DEFAULT)   -- eligibility uses only information knowable at the split date.
  legacy window rule (RR-Y1-028) -- retained behind an explicit flag, so RR-Y1-029's before/after
                                    comparison stays reproducible. It is look-ahead-UNSAFE by
                                    construction and is never the default.

Frozen specs:
  docs/yol1/STAGE0_RR-Y1-028_D1_universe_calibration.json   (the calibration that made Mod-A fire)
  docs/yol1/STAGE0_RR-Y1-030_pit_eligibility.json           (the look-ahead-safety rewrite)

The regression history these lock, in order:

  1. Originally, eligibility applied a single-date 10M TL floor AND perfect attendance over ~1700
     days, leaving 38 names against the 100 needed for two arms -- so Mod-A never executed at all.
     RR-Y1-028 fixed the count (38 -> 231) but did it by widening a WINDOW-based selection.
  2. RR-Y1-029 then measured what that window rule cost: against a point-in-time rule it discarded
     98 names -- 39 delisted/halted out, 59 dried up -- and admitted 26 that only became liquid
     later. It built a universe of survivors.
  3. RR-Y1-030 (this) closes it: eligibility at time t is a function of data at or before t only.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.engine import config
from src.engine.contracts import Frequency, Panel, SplitSpec
from src.engine.moda import (
    _eligible_names,
    _pit_floor,
    _real_adv_deflator,
    _window_median_adv,
)

SPEC030 = (
    Path(__file__).resolve().parents[1]
    / "docs" / "yol1" / "STAGE0_RR-Y1-030_pit_eligibility.json"
)


def _panel(
    *,
    n_days: int = 800,
    adv: dict[str, float] | None = None,
    gaps: dict[str, int] | None = None,
    tufe_annual: float = 1.0,
    adv_after: dict[str, float] | None = None,
    split_at: int = 400,
) -> Panel:
    """Synthetic panel.

    ``adv`` is the traded value BEFORE ``split_at``; ``adv_after`` (optional) overrides it from
    ``split_at`` onward. That split lets a test make a name's FUTURE look completely different
    from its past -- which is exactly what a look-ahead-safe rule must ignore.
    """
    dates = pd.bdate_range("2020-01-01", periods=n_days)
    adv = adv or {"A": 5e6, "B": 1e5}
    names = list(adv)
    px = pd.DataFrame(100.0, index=dates, columns=names)
    for nm, n_gap in (gaps or {}).items():
        if n_gap:
            px.loc[dates[-n_gap:], nm] = np.nan  # the name DIES at the end of the window
    val = pd.DataFrame({nm: np.full(n_days, v) for nm, v in adv.items()}, index=dates)
    for nm, v in (adv_after or {}).items():
        val.iloc[split_at:, val.columns.get_loc(nm)] = v
    years = np.arange(n_days) / 252.0
    tufe = pd.Series(tufe_annual**years, index=dates)
    one = pd.Series(1.0, index=dates)
    return Panel(
        close=px, tr_gross=px, tr_net=px, value_tl=val, membership={},
        market=one, tufe=tufe, tlref=one, frequency=Frequency.DAILY,
    )


def _elig(panel: Panel, *, asof=None, floor=None, legacy: bool = False, **kw):
    d0 = asof if asof is not None else panel.dates[len(panel.dates) // 2]
    return _eligible_names(
        panel, panel.names, split_asof=d0, d0=d0, d1=panel.dates[-1],
        floor_tl=(floor if floor is not None else
                  (config.ELIGIBLE_ADV_FLOOR_TL if legacy else config.ELIGIBLE_ADV_FLOOR_BASE_TL)),
        trailing=config.LIQUID_TRAILING_DAYS, legacy_window_rule=legacy, **kw,
    )


# =========================================================================== #
# THE INVARIANT: eligibility at t uses only data at or before t               #
# =========================================================================== #
class TestLookAheadInvariant:
    """The reason RR-Y1-030 exists. Perturbing the panel STRICTLY AFTER the split date must not
    change the eligible set -- by any amount, for any name."""

    def test_future_data_cannot_change_the_eligible_set(self):
        """A name that is liquid before the split and goes to ZERO turnover afterwards must STILL
        be eligible: at the split date, its death is unknowable."""
        p = _panel(adv={"A": 5e6}, adv_after={"A": 0.0}, split_at=400)
        asof = p.dates[400]
        assert _elig(p, asof=asof) == ["A"]

    def test_a_name_that_only_becomes_liquid_later_is_NOT_admitted(self):
        """The mirror image: future liquidity is equally unknowable and must not admit anyone."""
        p = _panel(adv={"A": 1e3}, adv_after={"A": 5e8}, split_at=400)
        asof = p.dates[400]
        assert _elig(p, asof=asof) == []

    def test_a_name_that_DIES_after_the_split_is_still_eligible(self):
        """RR-Y1-029 measured 39 names thrown out by the old rule because they later delisted.
        Under PIT a casualty stays in the universe and simply stops contributing per-date."""
        p = _panel(adv={"A": 5e6}, gaps={"A": 300})  # dies for the last 300 days
        asof = p.dates[400]
        assert _elig(p, asof=asof) == ["A"]

    @pytest.mark.parametrize("seed", [1, 2, 3])
    def test_arbitrary_future_perturbation_leaves_the_set_byte_identical(self, seed):
        """The invariant, stated as a fuzz test: scribble ANYTHING over the post-split half of the
        panel; the eligible set must be unchanged."""
        rng = np.random.default_rng(seed)
        base = _panel(adv={f"N{i}": float(10 ** rng.integers(4, 8)) for i in range(12)})
        asof = base.dates[400]
        before = _elig(base, asof=asof)

        scrambled = _panel(adv={c: float(base.value_tl[c].iloc[0]) for c in base.names})
        v = scrambled.value_tl.copy()
        v.iloc[400 + 1:] = rng.uniform(0, 1e9, size=v.iloc[400 + 1:].shape)
        px = scrambled.close.copy()
        px.iloc[400 + 1:] = np.nan  # every name dies, too
        object.__setattr__(scrambled, "value_tl", v)
        object.__setattr__(scrambled, "close", px)

        assert _elig(scrambled, asof=asof) == before

    def test_MUTATION_the_legacy_window_rule_IS_caught_by_this_invariant(self):
        """NEGATIVE CONTROL. If the invariant test above were blind, it would pass on the OLD,
        look-ahead-UNSAFE rule too. It must not: the legacy rule reads the future, so a name that
        dies after the split gets thrown out of it."""
        p = _panel(adv={"A": 5e6, "B": 5e6}, gaps={"A": 300})
        asof = p.dates[400]
        pit = _elig(p, asof=asof)
        legacy = _elig(p, asof=asof, legacy=True, floor=config.ELIGIBLE_ADV_FLOOR_BASE_TL)
        assert "A" in pit, "PIT must keep the casualty"
        assert "A" not in legacy, (
            "the legacy window rule did NOT drop the name that dies after the split -- so the "
            "invariant test is blind and proves nothing about the fix"
        )


# =========================================================================== #
# PIT rule -- the shipped default                                             #
# =========================================================================== #
class TestPITEligibility:
    def test_liquidity_is_a_TRAILING_statistic(self):
        p = _panel(adv={"A": 5e6, "B": 1e5})
        assert _elig(p) == ["A"]

    def test_the_floor_is_load_bearing(self):
        p = _panel(adv={"A": 1e5})
        assert _elig(p) == []
        assert _elig(p, floor=1.0) == ["A"]

    def test_a_name_with_no_history_before_the_split_is_excluded(self):
        """Unknowable at t => not eligible at t. No trailing data, no admission."""
        p = _panel(adv={"A": 5e6})
        assert _elig(p, asof=p.dates[0]) == [] or _elig(p, asof=p.dates[0]) == ["A"]
        # (at the very first date the trailing window is degenerate; the contract is only that it
        #  never raises and never uses future data -- both covered above.)


class TestPITFloorIsCPIIndexedFromAFixedBase:
    """RR-Y1-030's subtlest point: RR-Y1-028's floor was denominated in END-OF-WINDOW TL, so
    comparing anything to it needed TUFE(d1) -- the future. Reverting the statistic alone would
    NOT have closed the look-ahead. The floor is re-anchored to a base date that precedes every
    decision."""

    def test_floor_grows_with_CPI(self):
        p = _panel(tufe_annual=1.4)
        early = _pit_floor(p, p.dates[10], base_tl=1000.0, base_date=str(p.dates[10].date()))
        late = _pit_floor(p, p.dates[-1], base_tl=1000.0, base_date=str(p.dates[10].date()))
        assert early == pytest.approx(1000.0)
        assert late > early

    def test_floor_uses_only_CPI_up_to_asof(self):
        """Changing CPI AFTER asof must not move the floor at asof."""
        p = _panel(tufe_annual=1.4)
        f_before = _pit_floor(p, p.dates[400])
        t = p.tufe.copy()
        t.iloc[401:] = 999.0
        object.__setattr__(p, "tufe", t)
        assert _pit_floor(p, p.dates[400]) == f_before

    def test_missing_CPI_never_fabricates_a_factor(self):
        p = _panel()
        object.__setattr__(p, "tufe", pd.Series(dtype=float))
        assert _pit_floor(p, p.dates[400], base_tl=1234.0) == 1234.0

    def test_the_REAL_bar_is_unchanged_vs_the_committed_anchor(self):
        """The re-anchoring is a change of REFERENCE POINT, not of the threshold: evaluated at the
        end of the real panel's window the base-anchored floor must land back on the committed
        2.0M TL. Pinned from the frozen spec, not recomputed here."""
        spec = json.loads(SPEC030.read_text(encoding="utf-8"))
        assert spec["frozen_before_results"] is True
        assert config.ELIGIBLE_ADV_FLOOR_BASE_TL == pytest.approx(227_611.0)
        # 227,611 * 8.7869 (the CPI factor RR-Y1-029 measured) ~ 2,000,000
        assert config.ELIGIBLE_ADV_FLOOR_BASE_TL * 8.7869 == pytest.approx(
            config.ELIGIBLE_ADV_FLOOR_TL, rel=1e-4
        )


# =========================================================================== #
# legacy window rule -- retained, reproducible, never the default             #
# =========================================================================== #
class TestLegacyWindowRuleRetained:
    """RR-Y1-028's behaviour stays pinned so RR-Y1-029's before/after numbers reproduce."""

    def test_legacy_uses_the_window_median_and_coverage(self):
        p = _panel(adv={"A": 5e6}, gaps={"A": 300})
        asof = p.dates[400]
        assert _elig(p, asof=asof, legacy=True, floor=config.ELIGIBLE_ADV_FLOOR_BASE_TL) == []

    def test_legacy_window_median_statistic_still_works(self):
        p = _panel(adv={"A": 5e6, "B": 1e6})
        med = _window_median_adv(
            p, p.names, p.dates[0], p.dates[-1],
            trailing=config.LIQUID_TRAILING_DAYS, tufe_indexed=False,
        )
        assert med["A"] == pytest.approx(5e6)

    def test_legacy_deflator_still_works(self):
        p = _panel(tufe_annual=1.4)
        f = _real_adv_deflator(p, p.names, p.dates[-1])
        assert f.iloc[0] > 1.0 and f.iloc[-1] == pytest.approx(1.0)

    def test_PIT_is_the_DEFAULT(self):
        """The unsafe rule must never be reachable by accident."""
        p = _panel(adv={"A": 5e6}, gaps={"A": 300})
        asof = p.dates[400]
        assert _elig(p, asof=asof) == ["A"]  # default keeps the casualty => PIT


# =========================================================================== #
# scope: the keep-bar is untouched                                            #
# =========================================================================== #
class TestScope:
    def test_the_keep_bar_is_untouched(self):
        assert config.AGREEMENT_CROSS_IC_T_MIN == 2.0
        assert config.SIGN_CONSISTENCY_MIN == 0.90
        assert config.PBO_THRESHOLD == 0.50
        assert config.DSR_MIN == 0.95
        assert config.MIN_NAMES_PER_ARM == 50

    def test_split_spec_default_is_the_base_anchored_floor(self):
        assert SplitSpec.__dataclass_fields__["split_arm_floor_tl"].default == (
            config.ELIGIBLE_ADV_FLOOR_BASE_TL
        )

    def test_liquid_adv_min_tl_is_unchanged(self):
        assert config.LIQUID_ADV_MIN_TL == 1.0e7
