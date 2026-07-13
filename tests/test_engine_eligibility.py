"""RR-Y1-028 (D1a/b/c) -- Mod-A eligible-universe construction.

Frozen ex-ante in docs/yol1/STAGE0_RR-Y1-028_D1_universe_calibration.json.

The regression these lock: on the real BIST panel the Mod-A conjugate leg had never executed
once, because eligibility applied three filters that each independently starved it --

    D1a  liquidity sampled at a SINGLE date (the panel's earliest, thinnest point)
    D1b  a fixed NOMINAL TL floor in a ~40%/yr-inflation market (same floor: 48 names in 2019,
         169 in 2026 -- pure currency erosion)
    D1c  min_cov=1.0, i.e. perfect attendance for ~1700 trading days (a hidden survivorship
         filter: 681 -> 74 names)

-- leaving 38 eligible names against the 100 needed for two arms. So agreement_pass and the real
CSCV pbo were never produced for ANY candidate.

These tests pin the CONSTRUCTION, not any outcome. They must not encode "the leg fires"; that is
measured (and could have failed) in scripts/rr_y1_028_d1_calibration_result.py.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.engine import config
from src.engine.contracts import Frequency, Panel, SplitSpec
from src.engine.moda import _eligible_names, _real_adv_deflator, _window_median_adv


def _panel(
    *,
    n_days: int = 800,
    adv: dict[str, float] | None = None,
    gaps: dict[str, int] | None = None,
    tufe_annual: float = 1.0,
) -> Panel:
    """Synthetic panel with per-name ADV levels and an optional number of missing close-days."""
    dates = pd.bdate_range("2020-01-01", periods=n_days)
    adv = adv or {"A": 5e6, "B": 1e6}
    names = list(adv)
    px = pd.DataFrame(100.0, index=dates, columns=names)
    for nm, n_gap in (gaps or {}).items():
        if n_gap:
            px.loc[dates[:n_gap], nm] = np.nan
    val = pd.DataFrame({nm: np.full(n_days, v) for nm, v in adv.items()}, index=dates)
    years = np.arange(n_days) / 252.0
    tufe = pd.Series(tufe_annual**years, index=dates)
    one = pd.Series(1.0, index=dates)
    return Panel(
        close=px, tr_gross=px, tr_net=px, value_tl=val, membership={},
        market=one, tufe=tufe, tlref=one, frequency=Frequency.DAILY,
    )


def _elig(panel: Panel, **kw):
    d0, d1 = panel.dates[0], panel.dates[-1]
    return _eligible_names(
        panel, panel.names, split_asof=d0, d0=d0, d1=d1,
        floor_tl=kw.pop("floor_tl", config.ELIGIBLE_ADV_FLOOR_TL),
        trailing=config.LIQUID_TRAILING_DAYS,
        **kw,
    )


class TestD1cCoverageIsNotPerfectAttendance:
    def test_a_name_with_ordinary_halts_is_still_eligible(self):
        """~2% of days missing (a plausible year of halts/VBTS) must NOT disqualify a name."""
        panel = _panel(adv={"A": 5e6}, gaps={"A": 15})  # 15/800 = 1.9% missing
        assert _elig(panel, tufe_indexed=False) == ["A"]

    def test_a_name_that_barely_traded_is_excluded(self):
        """Coverage still bites: 20% missing is not an ordinary halt pattern."""
        panel = _panel(adv={"A": 5e6}, gaps={"A": 160})  # 20% missing
        assert _elig(panel, tufe_indexed=False) == []

    def test_the_old_perfect_attendance_rule_would_have_dropped_the_halted_name(self):
        """Pins the DEFECT: min_cov=1.0 removes a name for a single missing day."""
        panel = _panel(adv={"A": 5e6}, gaps={"A": 1})
        assert _elig(panel, tufe_indexed=False, min_coverage=1.0) == []
        assert _elig(panel, tufe_indexed=False) == ["A"]


class TestD1bFloorIsRealNotNominal:
    """The ADV series is deflated into END-OF-WINDOW TL and compared to a FLAT floor.

    Direction matters and is easy to get backwards: under inflation, EARLY-window turnover must
    be scaled UP (2019 TL bought more than 2026 TL), so the early window stops being penalised
    for the currency alone. A sign error here would make the bar HARSHER exactly where the old
    rule was already too harsh.
    """

    def test_deflator_is_unity_without_inflation(self):
        panel = _panel(tufe_annual=1.0)
        f = _real_adv_deflator(panel, panel.names, panel.dates[-1])
        assert f.iloc[0] == pytest.approx(1.0)
        assert f.iloc[-1] == pytest.approx(1.0)

    def test_deflator_scales_early_window_UP_under_inflation(self):
        """THE direction test. TUFE(end)/TUFE(t) > 1 early, == 1 at the end."""
        panel = _panel(tufe_annual=1.4)  # ~40%/yr
        f = _real_adv_deflator(panel, panel.names, panel.dates[-1])
        assert f.iloc[0] > 1.0
        assert f.iloc[-1] == pytest.approx(1.0)
        assert f.is_monotonic_decreasing

    def test_a_name_thin_in_nominal_terms_early_can_still_qualify(self):
        """A name whose NOMINAL turnover sits below the floor early, but whose REAL turnover
        clears it, must be eligible. Under the old nominal rule it was not."""
        panel = _panel(adv={"A": 1.2e6}, tufe_annual=1.5)  # nominal 1.2M < 2M floor
        assert _elig(panel, tufe_indexed=False) == []      # nominal bar: excluded
        assert _elig(panel, tufe_indexed=True) == ["A"]    # real bar: admitted

    def test_a_genuinely_illiquid_name_is_still_excluded(self):
        """Indexing removes a currency distortion; it does not open the gate to anyone."""
        panel = _panel(adv={"A": 1.0e5}, tufe_annual=1.5)
        assert _elig(panel, tufe_indexed=True) == []

    def test_missing_tufe_never_fabricates_a_deflator(self):
        panel = _panel()
        object.__setattr__(panel, "tufe", pd.Series(dtype=float))
        f = _real_adv_deflator(panel, panel.names, panel.dates[-1])
        assert (f == 1.0).all()


class TestD1aLiquidityIsAWindowStatistic:
    def test_a_single_thin_day_does_not_disqualify(self):
        """The old rule sampled ONE date. A name that was thin only on that date was lost."""
        panel = _panel(adv={"A": 5e6})
        panel.value_tl.iloc[:80, 0] = 1.0  # thin at the START -- exactly where d0 sampled
        # window median is still well above the floor -> eligible
        assert _elig(panel, tufe_indexed=False) == ["A"]

    def test_window_median_is_the_statistic(self):
        panel = _panel(adv={"A": 5e6, "B": 1e6})
        med = _window_median_adv(
            panel, panel.names, panel.dates[0], panel.dates[-1],
            trailing=config.LIQUID_TRAILING_DAYS, tufe_indexed=False,
        )
        assert med["A"] == pytest.approx(5e6)
        assert med["B"] == pytest.approx(1e6)


class TestFrozenConstantsAndScope:
    def test_constants_match_the_pre_registration(self):
        """The code must run the FROZEN values; drift is a discipline failure, not a detail."""
        import json
        from pathlib import Path

        prereg = json.loads(
            (
                Path(__file__).resolve().parents[1]
                / "docs" / "yol1" / "STAGE0_RR-Y1-028_D1_universe_calibration.json"
            ).read_text(encoding="utf-8")
        )
        fc = prereg["FROZEN_CONSTANTS"]
        assert prereg["frozen_before_results"] is True
        assert config.ELIGIBLE_ADV_FLOOR_TL == fc["ELIGIBLE_ADV_FLOOR_TL_END_OF_WINDOW"]
        assert config.ELIGIBLE_MIN_COVERAGE == fc["ELIGIBLE_MIN_COVERAGE"]
        assert config.ELIGIBLE_ADV_FLOOR_TUFE_INDEXED == fc["ELIGIBLE_ADV_FLOOR_IS_TUFE_INDEXED"]

    def test_the_keep_bar_is_untouched(self):
        """D1 recalibrates the UNIVERSE, never the bar (DEC-049)."""
        assert config.AGREEMENT_CROSS_IC_T_MIN == 2.0
        assert config.SIGN_CONSISTENCY_MIN == 0.90
        assert config.PBO_THRESHOLD == 0.50
        assert config.DSR_MIN == 0.95
        assert config.MIN_NAMES_PER_ARM == 50  # arm size NOT lowered

    def test_split_spec_default_is_the_calibrated_floor(self):
        assert SplitSpec.__dataclass_fields__["split_arm_floor_tl"].default == (
            config.ELIGIBLE_ADV_FLOOR_TL
        )

    def test_liquid_adv_min_tl_is_unchanged(self):
        """The old constant still governs data_adapter.liquid_names -- only Mod-A's eligibility
        floor moved. Changing both would have been scope creep."""
        assert config.LIQUID_ADV_MIN_TL == 1.0e7
