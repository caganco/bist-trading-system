"""RR-Y1-028-V — independent measurement-verification of the RR-Y1-028 engine fixes.

Frozen plan: docs/yol1/RR-Y1-028-V_verification_plan.json (written BEFORE any check ran).

GOVERNING PRINCIPLE (the reason this file exists at all):

    A fix's PASS is not evidence unless deliberately breaking the fix makes the check FAIL.

So every substantive claim here comes in a PAIR:
    test_<x>                 -- the check, on the shipped code. Must pass.
    test_<x>_MUTATION_kills  -- the same check, with the production behaviour monkeypatched
                                BACK TO THE BUG. Must fail (i.e. the assertion that the check
                                makes must be violated). A check that survives its own mutation
                                is BLIND and proves nothing.

Mutations are applied with monkeypatch inside the test process. NO production code is modified.

Scope: only the four RR-Y1-028 fixes. This is not a new bug hunt, not a re-measurement of any
candidate, and not a graveyard revival.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.engine import benchmark as bmk_mod
from src.engine import config
from src.engine import harness as harness_mod
from src.engine import keep_bar as kb_mod
from src.engine.benchmark import BenchmarkFloor, benchmark_floor
from src.engine.contracts import (
    AgreementConfidence,
    DialConfig,
    EngineOutput,
    Frequency,
    Panel,
    SortDepth,
    SplitMode,
    SplitSpec,
)
from src.engine.harness import _returns_cost, harness
from src.engine.keep_bar import Outcome, Verdict, adjudicate
from src.engine.stats import nw_tstat

PLAN = Path(__file__).resolve().parents[1] / "docs" / "yol1" / "RR-Y1-028-V_verification_plan.json"
HORIZONS = (1, 5, 10, 21, 63)


def test_plan_was_frozen_before_results():
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    assert plan["frozen_before_results"] is True


# --------------------------------------------------------------------------- #
# fixtures                                                                     #
# --------------------------------------------------------------------------- #
class _StaticSignal:
    """A fixed score vector, identical every date, parameterized only by h.

    The BASKET it selects is therefore the same at every horizon -- only the forward-return
    window changes. That is what makes the h-invariance relation in D2_1 exact-in-principle.
    """

    def __init__(self, h: int, names: list[str]) -> None:
        self.name = f"static_h{h}"
        self.construction_window = int(h)
        self._vec = pd.Series(np.linspace(1.0, 0.0, len(names)), index=names)

    def scores(self, panel: Panel, names: list[str], asof: pd.Timestamp) -> pd.Series:
        return self._vec.reindex(names)


def _panel(*, n_days: int = 1200, n_names: int = 60, cpi_annual: float = 1.20,
           daily_vol: float = 0.004, market_drift: float = 0.0, seed: int = 3) -> Panel:
    """Synthetic panel.

    ``market_drift`` is a COMMON daily drift added to every name. It cancels out of the ACTIVE
    spread (it lifts the tilt and its EW benchmark equally), so it does not disturb the D2
    h-invariance relation -- but it is what makes the BENCHMARK's own return non-trivial, which
    the D3 gate tests need (see the D3 fixture below).

    Daily returns are kept small so that mean(overlapping h-day active) ~ h * mean(daily active)
    holds tightly; that linearity is the premise of the D2 metamorphic relation.
    """
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2019-01-01", periods=n_days)
    names = [f"N{i:02d}" for i in range(n_names)]
    xs = np.linspace(0.00025, -0.00025, n_names)  # persistent cross-sectional spread
    steps = rng.normal(0.0, daily_vol, size=(n_days, n_names)) + xs + market_drift
    px = pd.DataFrame(100.0 * np.exp(np.cumsum(steps, axis=0)), index=dates, columns=names)
    val = pd.DataFrame(5e7, index=dates, columns=names)
    mkt = pd.Series(100.0 * np.exp(np.cumsum(rng.normal(0, 0.006, n_days))), index=dates)
    yrs = np.arange(n_days) / 252.0
    tufe = pd.Series(cpi_annual**yrs, index=dates)
    tlref = pd.Series(1.0, index=dates)
    return Panel(close=px, tr_gross=px, tr_net=px, value_tl=val, membership={},
                 market=mkt, tufe=tufe, tlref=tlref, frequency=Frequency.DAILY)


@pytest.fixture(scope="module")
def panel() -> Panel:
    """D2's instrument: NO market drift, so the arithmetic-vs-compound gap stays negligible and
    the h-invariance relation is tight."""
    return _panel()


@pytest.fixture(scope="module")
def growth_panel() -> Panel:
    """D3's instrument -- and it must be built deliberately.

    The FIRST attempt at these D3 checks used the drift-free panel above and both of them came
    back VACUOUS: with an EW benchmark returning ~0.5%/yr against 20% CPI, the strategy loses to
    inflation under BOTH the old and the new gate, so `beats_benchmark_floor` never moves and the
    old-vs-new difference is unobservable. The check reported its own blindness rather than
    passing silently -- which is the whole point of the protocol.

    A meaningful D3 bed needs the BENCHMARK ITSELF to clear the floor, so that the two gates can
    disagree: old (judging the tilt alone, ~5%) must FAIL, new (judging benchmark + tilt, ~40%)
    must PASS. Hence a common drift of ~35%/yr against 20% CPI.
    """
    return _panel(market_drift=0.0012, cpi_annual=1.20)


@pytest.fixture(scope="module")
def spec() -> SplitSpec:
    return SplitSpec(split_mode=SplitMode.NAME, frequency=Frequency.DAILY, embargo_h=1,
                     sort_depth=SortDepth.TERCILE)


def _gross_at(panel: Panel, spec: SplitSpec, h: int) -> float:
    return _returns_cost(panel, _StaticSignal(h, panel.names), spec, DialConfig()).gross_active_ann


def _h_spread(panel: Panel, spec: SplitSpec) -> float:
    """max/min of |gross_active_ann| across HORIZONS. The metric both D2_1 and its mutation read."""
    vals = [abs(_gross_at(panel, spec, h)) for h in HORIZONS]
    assert all(np.isfinite(v) and v > 0 for v in vals), vals
    return max(vals) / min(vals)


# =========================================================================== #
# D2 -- annualizing an overlapping horizon                                    #
# =========================================================================== #
class TestD2Annualization:
    """Relation (derived in the frozen plan; the task text's 'gross_ann x h' is a slip):

        active.mean() ~ h * mu_1        (mean of OVERLAPPING h-day active returns)
        gross_ann     = active.mean() * (252/h) ~ 252 * mu_1   -> INDEPENDENT of h

    The old code used *252, giving ~252*h*mu_1 -> PROPORTIONAL to h. So the corrected
    gross_active_ann must be h-INVARIANT, and the bug must show up as h-proportionality.
    """

    def test_D2_1_gross_is_h_invariant(self, panel, spec):
        spread = _h_spread(panel, spec)
        assert spread < 1.25, (
            f"gross_active_ann varies by {spread:.2f}x across h in {HORIZONS} -- it must be "
            "h-invariant. The annualizer is still horizon-dependent somewhere."
        )

    def test_D2_1_MUTATION_kills_h_invariance(self, panel, spec, monkeypatch):
        """NEGATIVE CONTROL: put the bug back (annualizer -> 252 regardless of h).
        The invariance check MUST break. If it does not, D2_1 is blind."""
        monkeypatch.setattr(harness_mod, "_annualizer", lambda yr, h: yr)
        spread = _h_spread(panel, spec)
        assert spread > 10.0, (
            f"the reinstated bug produced only a {spread:.2f}x spread -- test_D2_1 is BLIND and "
            "proves nothing about the fix."
        )

    def test_D2_3_old_code_scaled_with_h(self, panel, spec, monkeypatch):
        """POSITIVE CONTROL FOR THE BUG: under the mutation, gross_ann(h)/gross_ann(1) ~ h.
        This proves the defect was real and h-proportional -- the premise of the whole fix."""
        monkeypatch.setattr(harness_mod, "_annualizer", lambda yr, h: yr)
        g1 = _gross_at(panel, spec, 1)
        for h in (5, 21):
            ratio = _gross_at(panel, spec, h) / g1
            assert 0.8 * h < ratio < 1.2 * h, (
                f"old-code gross_ann(h={h})/gross_ann(1) = {ratio:.2f}, expected ~{h}"
            )

    def test_D2_2_h1_is_byte_identical_to_pre_fix(self, panel, spec):
        """ZERO-REGRESSION, as an exact identity: at h=1 the corrected annualizer (252/1) IS
        the old one (252). Exact float equality, not approx."""
        rc = _returns_cost(panel, _StaticSignal(1, panel.names), spec, DialConfig())
        pre_fix = float(rc.active.mean() * config.TRADING_DAYS_YR)
        assert rc.gross_active_ann == pre_fix

    def test_D2_4a_nw_lag_widens_with_h(self):
        d = DialConfig()
        assert d.nw_lag_for(Frequency.DAILY, h=1) == config.NW_LAG_DAILY
        assert d.nw_lag_for(Frequency.DAILY, h=21) == 21
        assert d.nw_lag_for(Frequency.DAILY, h=63) == 63
        assert DialConfig(nw_lag=7).nw_lag_for(Frequency.DAILY, h=21) == 7  # explicit wins

    def test_D2_4b_narrow_bandwidth_inflates_t_on_an_overlapping_series(self, panel, spec):
        """The REASON the bandwidth must widen: on a 21-day overlapping series a lag-5 HAC
        understates the standard error, so |t| comes out too large."""
        rc = _returns_cost(panel, _StaticSignal(21, panel.names), spec, DialConfig())
        a = rc.active.to_numpy(dtype=float)
        t5 = abs(nw_tstat(a, lag=5))
        t21 = abs(nw_tstat(a, lag=21))
        assert t21 < t5, f"widening the HAC bandwidth did not reduce |t| ({t21:.3f} vs {t5:.3f})"

    def test_D2_4c_the_widening_is_actually_WIRED_INTO_the_harness(self, panel, spec, monkeypatch):
        """It is not enough that nw_lag_for CAN widen -- _returns_cost must USE it.
        MUTATION: force nw_lag_for to ignore h; the harness's emitted nw_t must then change."""
        shipped = _returns_cost(panel, _StaticSignal(21, panel.names), spec, DialConfig()).nw_t
        monkeypatch.setattr(
            DialConfig, "nw_lag_for",
            lambda self, frequency, h=1: config.NW_LAG_DAILY,
        )
        mutated = _returns_cost(panel, _StaticSignal(21, panel.names), spec, DialConfig()).nw_t
        assert shipped != mutated, (
            "forcing the HAC bandwidth back to 5 did not change the emitted nw_t -- the h-aware "
            "lag is NOT wired into _returns_cost."
        )
        assert abs(mutated) > abs(shipped)  # and the bug inflates it, as claimed


# =========================================================================== #
# D3 -- the benchmark floor                                                   #
# =========================================================================== #
def _old_benchmark_floor(nominal_total_ann, panel, d0, d1, *, nominal_active_ann=None,
                         tlref_from=config.BENCHMARK_TLREF_FROM) -> BenchmarkFloor:
    """The PRE-FIX gate, re-executed on purpose: deflate the ACTIVE spread, compare REAL vs
    NOMINAL floor. Signature matches the new one so it can be dropped into the harness."""
    real = benchmark_floor(nominal_total_ann, panel, d0, d1,
                           nominal_active_ann=nominal_active_ann, tlref_from=tlref_from)
    x = nominal_active_ann if nominal_active_ann is not None else nominal_total_ann
    old_real_active = (1.0 + x) / (1.0 + real.tufe_ann) - 1.0
    beats = (
        bool(old_real_active > real.benchmark_floor_ann)
        if np.isfinite(old_real_active) and np.isfinite(real.benchmark_floor_ann)
        else None
    )
    return BenchmarkFloor(
        real_total_ann=old_real_active,               # the old code's "real_active_ann"
        benchmark_floor_ann=real.benchmark_floor_ann,
        benchmark_floor_real_ann=real.benchmark_floor_real_ann,
        beats_benchmark_floor=beats,
        real_active_ann=old_real_active,
        tufe_ann=real.tufe_ann, tlref_ann=real.tlref_ann,
        guard_raised=real.guard_raised, guard_messages=real.guard_messages,
    )


_FLOOR_FIELDS = {
    "real_total_ann", "real_active_ann", "benchmark_floor_ann", "benchmark_floor_real_ann",
    "beats_benchmark_floor", "strategy_total_ann", "benchmark_ew_ann",
}


class TestD3BenchmarkFloor:
    def test_D3_0_the_bed_is_not_vacuous(self, growth_panel, spec):
        """GUARD ON THE GUARD. D3_1 can only observe the fix if the two gates CAN disagree here:
        the benchmark must itself clear the floor while the tilt alone cannot. Assert that
        precondition explicitly, so a future panel change cannot silently make D3_1 vacuous
        (which is exactly what the first version of this file did)."""
        rc = _returns_cost(growth_panel, _StaticSignal(1, growth_panel.names), spec, DialConfig())
        floor = benchmark_floor(0.0, growth_panel, rc.d0, rc.d1).benchmark_floor_ann
        assert rc.bench_ann > floor, (
            f"vacuous bed: EW benchmark {rc.bench_ann:.2%} does not clear the floor "
            f"{floor:.2%}, so old and new gates would both say False"
        )
        assert rc.net_active_ann < floor, (
            "vacuous bed: the tilt ALONE clears the floor, so even the buggy gate would pass"
        )

    def test_D3_1_difference_is_confined_to_the_floor_path(self, growth_panel, spec, monkeypatch):
        """ISOLATION. Run the harness shipped vs with the OLD floor patched in. Every field that
        is not on the floor path must be IDENTICAL -- the fix must not have moved anything else."""
        sig = _StaticSignal(1, growth_panel.names)
        new = harness(growth_panel, sig, spec, DialConfig())
        monkeypatch.setattr(harness_mod, "benchmark_floor", _old_benchmark_floor)
        old = harness(growth_panel, sig, spec, DialConfig())

        moved, unchanged = [], []
        for f in vars(new):
            a, b = getattr(new, f), getattr(old, f)
            same = (a == b) or (
                isinstance(a, float) and isinstance(b, float)
                and np.isnan(a) and np.isnan(b)
            )
            (unchanged if same else moved).append(f)

        assert set(moved) <= _FLOOR_FIELDS, (
            f"the D3 fix moved fields OUTSIDE the floor path: {sorted(set(moved) - _FLOOR_FIELDS)}"
        )
        # and it must have moved the VERDICT, or the check is vacuous (see D3_0)
        assert "beats_benchmark_floor" in moved
        assert new.beats_benchmark_floor is True and old.beats_benchmark_floor is False
        for f in ("gross_active_ann", "net_active_ann", "cost_ann", "nw_t", "n_obs"):
            assert f in unchanged, f"{f} changed -- the fix leaked outside the gate"

    def test_D3_2_MECHANICAL_the_deflator_receives_the_TOTAL_not_the_spread(
        self, growth_panel, spec, monkeypatch
    ):
        """Code-path assertion, not a claim: spy on what the harness actually hands the gate."""
        seen: dict[str, float] = {}

        def spy(nominal_total_ann, p, d0, d1, *, nominal_active_ann=None, **kw):
            seen["total"] = nominal_total_ann
            seen["active"] = nominal_active_ann
            return benchmark_floor(nominal_total_ann, p, d0, d1,
                                   nominal_active_ann=nominal_active_ann, **kw)

        monkeypatch.setattr(harness_mod, "benchmark_floor", spy)
        out = harness(growth_panel, _StaticSignal(1, growth_panel.names), spec, DialConfig())

        assert seen["total"] == pytest.approx(out.benchmark_ew_ann + out.net_active_ann)
        assert seen["active"] == pytest.approx(out.net_active_ann)
        # non-vacuous: on a bed where the benchmark carries a real return, the TOTAL and the
        # SPREAD are far apart -- so passing one instead of the other is observable.
        assert abs(seen["total"] - seen["active"]) > 0.05, (
            "the benchmark leg is ~0 on this panel, so total ~ spread and the assertion above "
            "cannot distinguish them (vacuous)"
        )

    @pytest.mark.parametrize("cpi", [0.20, 0.38, 0.60])
    @pytest.mark.parametrize("tilt", [0.05, 0.10, -0.05])
    def test_D3_3_sanity_grid(self, cpi, tilt):
        """3 tilts x 3 CPI levels. The EW benchmark is set 20pp ABOVE inflation, so the STRATEGY
        genuinely beats the floor in every cell (even the -5% tilt: 0.20-0.05 = +15pp of headroom).

        OLD gate: must FAIL every cell -- it judged the tilt alone, and no tilt of a few percent
                  can out-run inflation. That is the bug, PROVEN here rather than asserted.
        NEW gate: must PASS every cell -- because the strategy's TOTAL return does clear the floor.
        """
        p = _panel(cpi_annual=1.0 + cpi, n_days=800)
        d0, d1 = p.dates[0], p.dates[-1]
        bench = cpi + 0.20
        total = bench + tilt

        new = benchmark_floor(total, p, d0, d1, nominal_active_ann=tilt)
        old = _old_benchmark_floor(total, p, d0, d1, nominal_active_ann=tilt)

        assert new.beats_benchmark_floor is True, (
            f"cpi={cpi:.0%} tilt={tilt:+.0%}: total {total:.2%} vs floor "
            f"{new.benchmark_floor_ann:.2%} -- the corrected gate should pass this"
        )
        assert old.beats_benchmark_floor is False, (
            f"cpi={cpi:.0%} tilt={tilt:+.0%}: the OLD gate passed this cell, so the bug this fix "
            "claims to repair does not reproduce -- the premise of D3 is unproven"
        )

    def test_D3_3b_new_gate_still_FAILS_a_strategy_that_loses_to_inflation(self):
        """The corrected gate must not be a rubber stamp: a strategy whose TOTAL return trails
        inflation must still fail, however large its tilt."""
        p = _panel(cpi_annual=1.60, n_days=800)
        d0, d1 = p.dates[0], p.dates[-1]
        bf = benchmark_floor(0.10 + 0.30, p, d0, d1, nominal_active_ann=0.30)  # total 40% < 60%
        assert bf.beats_benchmark_floor is False

    def test_D3_4_strangler_legacy_field_is_byte_preserved(self):
        p = _panel(cpi_annual=1.38, n_days=800)
        d0, d1 = p.dates[0], p.dates[-1]
        active, total = 0.05, 0.65
        bf = benchmark_floor(total, p, d0, d1, nominal_active_ann=active)
        expected_old = (1.0 + active) / (1.0 + bf.tufe_ann) - 1.0
        assert bf.real_active_ann == expected_old          # exact, not approx
        # ... and it was NOT quietly repointed at the new quantity
        assert bf.real_active_ann != pytest.approx(bf.real_total_ann)
        assert bf.real_active_ann < 0 < bf.real_total_ann  # they even have opposite signs here


# =========================================================================== #
# D1d -- NOT_MEASURED is not FAIL (and, critically, FAIL is still FAIL)       #
# =========================================================================== #
def _out(**over) -> EngineOutput:
    base = dict(agreement_pass=True, agreement_measured=True, pbo=0.10, pbo_measured=True,
                dsr=0.99, net_active_ann=0.05, beats_benchmark_floor=True)
    base.update(over)
    return EngineOutput(**base)


_MEASURED_FAILS = {
    "agreement_pass": dict(agreement_pass=False, agreement_measured=True),
    "pbo<=max": dict(pbo=0.80, pbo_measured=True),
    "dsr>=min": dict(dsr=0.10),
    "net_active_ann>0": dict(net_active_ann=-0.02),
    "beats_benchmark_floor": dict(beats_benchmark_floor=False),
}


class TestD1dTriState:
    def test_D1d_1_three_paths(self):
        assert adjudicate(_out()).verdict is Verdict.KEEP
        assert adjudicate(_out(agreement_pass=False)).verdict is Verdict.DROP
        assert adjudicate(
            _out(agreement_pass=None, agreement_measured=False)
        ).verdict is Verdict.INCONCLUSIVE

    @pytest.mark.parametrize("cond", sorted(_MEASURED_FAILS))
    def test_D1d_2a_NEGATIVE_CONTROL_every_measured_fail_still_DROPS(self, cond):
        """THE critical control. If the D1d fix laundered real negatives into INCONCLUSIVE, a
        failing candidate would stop failing -- the most dangerous possible regression."""
        r = adjudicate(_out(**_MEASURED_FAILS[cond]))
        assert r.conditions[cond] is Outcome.FAIL
        assert r.verdict is Verdict.DROP
        assert cond in r.failed and cond not in r.not_measured

    def test_D1d_2b_a_real_FAIL_beats_a_NOT_MEASURED(self):
        """A genuine failure must remain decisive even when another gate was never measured:
        DROP must not soften to INCONCLUSIVE just because something is missing."""
        r = adjudicate(_out(agreement_pass=None, agreement_measured=False, net_active_ann=-0.02))
        assert r.verdict is Verdict.DROP
        assert r.failed == ["net_active_ann>0"]
        assert r.not_measured == ["agreement_pass"]

    def test_D1d_2c_all_conditions_failing_still_DROPS(self):
        allfail = {k: v for d in _MEASURED_FAILS.values() for k, v in d.items()}
        assert adjudicate(_out(**allfail)).verdict is Verdict.DROP

    def test_D1d_2_MUTATION_kills_the_negative_control(self, monkeypatch):
        """Force the tri-state reducer to call everything NOT_MEASURED -- i.e. exactly the
        laundering bug the control exists to catch. Every measured-FAIL assertion must now break.
        If any survives, that control is blind."""
        monkeypatch.setattr(kb_mod, "_tri", lambda measured, passed: Outcome.NOT_MEASURED)
        survivors = []
        for cond, over in _MEASURED_FAILS.items():
            r = adjudicate(_out(**over))
            if r.verdict is Verdict.DROP or cond in r.failed:
                survivors.append(cond)
        assert not survivors, (
            f"the laundering mutation did NOT break the control for {survivors} -- those "
            "negative controls are blind and D1d is unverified for them."
        )
        # and it produces exactly the dangerous outcome we claim to be guarding against
        assert adjudicate(_out(agreement_pass=False)).verdict is Verdict.INCONCLUSIVE


# =========================================================================== #
# D1a/b/c -- eligibility (real-panel; skipped when the data layer is absent)  #
# =========================================================================== #
_HAS_DATA = config.PRICES_PARQUET.exists()
pytestmark_data = pytest.mark.skipif(not _HAS_DATA, reason="clean_universe parquet not present")


@pytest.mark.skipif(not _HAS_DATA, reason="clean_universe parquet not present")
class TestD1abcEligibilityAttribution:
    """Which filter ACTUALLY unblocked Mod-A? The RR-Y1-028 report claims 'each filter is
    independently below the bar, so fixing one alone would not have helped'. That claim is
    testable -- and this check can DISCONFIRM it. That is the point of running it."""

    @staticmethod
    def _counts():
        from src.engine.data_adapter import load_panel
        from src.engine.moda import _eligible_names, _trailing_adv
        from src.engine.data_adapter import continuous_basket

        p = load_panel()
        d0, d1 = pd.Timestamp("2019-07-03"), pd.Timestamp("2026-04-22")
        tr = config.LIQUID_TRAILING_DAYS

        # (i) the OLD rule, reconstructed exactly: single-date 10M floor + perfect attendance
        adv_d0 = _trailing_adv(p, p.names, d0, trailing=tr)
        liquid_old = [str(n) for n in adv_d0[adv_d0 >= config.LIQUID_ADV_MIN_TL].dropna().index]
        old = len(continuous_basket(p, d0, d1, names=liquid_old, min_cov=1.0))

        # (ii) coverage relaxation ONLY (old single-date 10M floor, cov 0.95)
        cov_only = len(continuous_basket(p, d0, d1, names=liquid_old, min_cov=0.95))

        # (iii) tradability floor ONLY (new floor + window median + CPI, but perfect attendance)
        floor_only = len(_eligible_names(
            p, p.names, split_asof=d0, d0=d0, d1=d1,
            floor_tl=config.ELIGIBLE_ADV_FLOOR_TL, trailing=tr, min_coverage=1.0,
        ))

        # (iv) the shipped calibration
        both = len(_eligible_names(
            p, p.names, split_asof=d0, d0=d0, d1=d1,
            floor_tl=config.ELIGIBLE_ADV_FLOOR_TL, trailing=tr,
        ))
        return old, cov_only, floor_only, both

    def test_D1abc_1_attribution(self):
        need = 2 * config.MIN_NAMES_PER_ARM
        old, cov_only, floor_only, both = self._counts()
        print(f"\n[D1abc attribution] old={old}  coverage_only={cov_only}  "
              f"floor_only={floor_only}  shipped={both}  (need {need})")

        assert old < need, "the OLD rule was supposed to block Mod-A; it did not"
        assert both >= need, "the shipped calibration must make Mod-A executable"

        # The report's claim: NEITHER single fix would have sufficed.
        assert cov_only < need, (
            f"REPORT CLAIM DISCONFIRMED: relaxing coverage ALONE already yields {cov_only} >= "
            f"{need} names. The statement 'each filter is independently below the bar' is FALSE "
            "and the RR-Y1-028 report must be corrected."
        )
        assert floor_only < need, (
            f"REPORT CLAIM DISCONFIRMED: the tradability floor ALONE already yields {floor_only} "
            f">= {need} names. The report's attribution must be corrected."
        )

    def test_D1abc_2_the_floor_is_load_bearing(self):
        """Negative control: the floor must actually exclude someone. If dropping it to ~0
        changes nothing, the tradability anchor is decoration."""
        from src.engine.data_adapter import load_panel
        from src.engine.moda import _eligible_names

        p = load_panel()
        d0, d1 = pd.Timestamp("2019-07-03"), pd.Timestamp("2026-04-22")
        shipped = len(_eligible_names(p, p.names, split_asof=d0, d0=d0, d1=d1,
                                      floor_tl=config.ELIGIBLE_ADV_FLOOR_TL,
                                      trailing=config.LIQUID_TRAILING_DAYS))
        no_floor = len(_eligible_names(p, p.names, split_asof=d0, d0=d0, d1=d1,
                                       floor_tl=1.0,
                                       trailing=config.LIQUID_TRAILING_DAYS))
        assert no_floor > shipped, "the floor excludes nobody -- it is decorative, not load-bearing"

    def test_D1abc_3_MUTATION_inverting_the_deflator_hurts(self):
        """The CPI deflator's DIRECTION is load-bearing: inverting it (TUFE(t)/TUFE(end), i.e.
        scaling early turnover DOWN) must SHRINK the eligible pool. If inverting it changes
        nothing, the indexing is cosmetic and D1b is unverified."""
        from src.engine.data_adapter import load_panel
        from src.engine.moda import _window_median_adv, _real_adv_deflator
        from src.engine.data_adapter import continuous_basket

        p = load_panel()
        d0, d1 = pd.Timestamp("2019-07-03"), pd.Timestamp("2026-04-22")
        tr = config.LIQUID_TRAILING_DAYS

        correct = _window_median_adv(p, p.names, d0, d1, trailing=tr, tufe_indexed=True)
        n_correct = len(continuous_basket(
            p, d0, d1,
            names=[str(n) for n in correct[correct >= config.ELIGIBLE_ADV_FLOOR_TL].dropna().index],
            min_cov=config.ELIGIBLE_MIN_COVERAGE,
        ))

        inv = 1.0 / _real_adv_deflator(p, p.names, d1)
        v = p.value_tl[p.names].astype(float).mul(inv, axis=0)
        trail = v.rolling(tr, min_periods=max(5, tr // 3)).median()
        win = trail.loc[(trail.index >= d0) & (trail.index <= d1)].median(skipna=True)
        n_inverted = len(continuous_basket(
            p, d0, d1,
            names=[str(n) for n in win[win >= config.ELIGIBLE_ADV_FLOOR_TL].dropna().index],
            min_cov=config.ELIGIBLE_MIN_COVERAGE,
        ))

        print(f"\n[D1abc deflator direction] correct={n_correct}  inverted={n_inverted}")
        assert n_inverted < n_correct, (
            "inverting the CPI deflator did not shrink the eligible pool -- the indexing "
            "direction is not load-bearing, so D1b is unverified."
        )
