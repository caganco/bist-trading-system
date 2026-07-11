"""RR-Y1-027 — ideal / frictionless measurement layer (DEC-064).

Tier-A tests for ``src/engine/frictionless.py`` PLUS the embedded measurement-
verification protocol (differential / metamorphic / placebo + look-ahead-injection).

The §6 IPO validation is a SYNTHETIC, deterministic golden fixture (NON-VERDICT /
SYNTHETIC-CALIBRATION) — the real S#21 n=24 IPO panel is not committed in any repo,
so per the maintainer's revised §6 the capability is validated MECHANICALLY here and
the real-data n=24 validation is DEFERRED (recorded in RESEARCH_REGISTRY). This fixture
is NOT an IPO finding; it freezes the layer's mechanics, exactly like the MTH SIZE/POWER
golden freezes the multiple-testing harness mechanics.

Additivity is asserted directly (``TestAdditivityVsHarness``): the layer reproduces the
committed harness's gross/net numbers unchanged — the verdict layer does not move.
"""
from __future__ import annotations

import numpy as np
import pytest

from src.engine.contracts import DialConfig, Frequency, Panel, SplitMode, SplitSpec
from src.engine.frictionless import (
    LABEL_IDEAL,
    LABEL_REALISTIC,
    DualLayerReport,
    FrictionParams,
    apply_friction,
    dual_layer_report,
    friction_grave_hint,
    from_engine_output,
    position_fingerprint,
)
from src.engine.harness import harness


# --------------------------------------------------------------------------- #
# §4 — differential invariant (the layer's load-bearing correctness property)  #
# --------------------------------------------------------------------------- #
class TestDifferentialInvariant:
    def test_null_friction_is_identity(self):
        for g in (-0.25, 0.0, 0.0123456789, 0.40, 1.5):
            assert apply_friction(g, FrictionParams.null()) == g

    def test_nan_gross_stays_nan(self):
        assert np.isnan(apply_friction(float("nan"), FrictionParams.null()))
        assert np.isnan(apply_friction(float("nan"), FrictionParams(cost_ann=0.02)))

    def test_realistic_at_null_reproduces_ideal_bit_for_bit(self):
        # The §4 invariant on a non-trivial friction: re-costing the realistic gross
        # with null friction must equal the ideal net exactly.
        rep = dual_layer_report(
            0.40,
            FrictionParams(cost_ann=0.015, tax_ann=0.004, fill_fraction=0.10,
                           access_haircut_ann=0.04),
            shared_position_fingerprint="x",
            strong_ideal_ann=0.10, dead_realistic_band=0.0,
        )
        assert rep.differential_invariant_holds()
        assert rep.ideal.net_active_ann == rep.ideal.gross_active_ann == 0.40
        assert apply_friction(rep.realistic.gross_active_ann, FrictionParams.null()) == \
            rep.ideal.net_active_ann

    def test_shared_position_series_one_fingerprint(self):
        # Both layers consume ONE position series -> identical gross, one fingerprint.
        rep = dual_layer_report(
            0.123, FrictionParams(cost_ann=0.02), shared_position_fingerprint="fp123",
            strong_ideal_ann=0.10, dead_realistic_band=0.0,
        )
        assert rep.realistic.gross_active_ann == rep.ideal.gross_active_ann
        assert rep.shared_position_fingerprint == "fp123"


# --------------------------------------------------------------------------- #
# §5 — output contract: ideal is NON-VERDICT / CONCEPT-LEDGER, realistic is the #
# verdict; the tag survives into the machine-readable dict                      #
# --------------------------------------------------------------------------- #
class TestOutputContract:
    def _rep(self) -> DualLayerReport:
        return dual_layer_report(
            0.40, FrictionParams(cost_ann=0.015, fill_fraction=0.10, access_haircut_ann=0.04),
            shared_position_fingerprint="x", strong_ideal_ann=0.10, dead_realistic_band=0.0,
        )

    def test_ideal_is_non_verdict_and_labelled(self):
        rep = self._rep()
        assert rep.ideal.is_verdict is False
        assert "NON-VERDICT" in rep.ideal.label and "CONCEPT-LEDGER" in rep.ideal.label
        assert rep.ideal.label == LABEL_IDEAL

    def test_realistic_is_the_verdict(self):
        rep = self._rep()
        assert rep.realistic.is_verdict is True
        assert rep.realistic.label == LABEL_REALISTIC

    def test_non_verdict_tag_survives_serialization(self):
        d = self._rep().to_dict()
        assert d["ideal"]["NON_VERDICT"] is True
        assert d["ideal"]["concept_ledger"] is True
        assert "NON_VERDICT" not in d["realistic"]  # the verdict layer is unannotated


# --------------------------------------------------------------------------- #
# §5 — friction-grave classification HOOK (possible, never automatic)           #
# --------------------------------------------------------------------------- #
class TestFrictionGraveHook:
    def test_strong_ideal_dead_realistic_tradability_bound_is_candidate(self):
        rep = dual_layer_report(
            0.40, FrictionParams(cost_ann=0.015, fill_fraction=0.10, access_haircut_ann=0.04),
            shared_position_fingerprint="x", strong_ideal_ann=0.10, dead_realistic_band=0.0,
        )
        h = rep.friction_grave_hint
        assert h["candidate"] is True
        assert h["requires_human"] is True  # the layer NEVER auto-decides
        assert "friction-grave" in h["reason"]

    def test_pure_money_cost_gap_is_not_a_friction_grave(self):
        # Same strong ideal, killed by money-cost ALONE (full fill, no access slip):
        # that is a plain cost-fail, NOT a friction-grave.
        rep = dual_layer_report(
            0.40, FrictionParams(cost_ann=0.45, fill_fraction=1.0, access_haircut_ann=0.0),
            shared_position_fingerprint="x", strong_ideal_ann=0.10, dead_realistic_band=0.0,
        )
        h = rep.friction_grave_hint
        assert h["candidate"] is False
        assert h["tradability_bound"] is False
        assert "money-cost" in h["reason"]
        assert h["requires_human"] is True

    def test_weak_ideal_is_no_grave(self):
        rep = dual_layer_report(
            0.03, FrictionParams(fill_fraction=0.10), shared_position_fingerprint="x",
            strong_ideal_ann=0.10, dead_realistic_band=0.0,
        )
        assert rep.friction_grave_hint["candidate"] is False
        assert rep.friction_grave_hint["strong_ideal"] is False


# --------------------------------------------------------------------------- #
# §7 — measurement-verification: METAMORPHIC (necessary input->output relations)#
# --------------------------------------------------------------------------- #
class TestMetamorphic:
    def test_monotone_in_cost(self):
        g = 0.40
        nets = [apply_friction(g, FrictionParams(cost_ann=c)) for c in (0.0, 0.05, 0.10, 0.20)]
        assert nets == sorted(nets, reverse=True)  # more cost -> strictly lower net
        assert nets[0] == g                          # cost=0 boundary == ideal

    def test_monotone_in_access_haircut(self):
        g = 0.40
        nets = [apply_friction(g, FrictionParams(access_haircut_ann=a))
                for a in (0.0, 0.05, 0.10, 0.20)]
        assert nets == sorted(nets, reverse=True)

    def test_monotone_in_fill_fraction(self):
        g = 0.40  # positive gross -> LESS fill = LESS net
        nets = [apply_friction(g, FrictionParams(fill_fraction=f)) for f in (1.0, 0.5, 0.2, 0.05)]
        assert nets == sorted(nets, reverse=True)

    def test_converges_to_ideal_at_friction_zero(self):
        g = 0.40
        approaching = [
            apply_friction(g, FrictionParams(cost_ann=c, access_haircut_ann=c, fill_fraction=1.0 - c))
            for c in (0.10, 0.01, 0.001, 0.0)
        ]
        assert approaching[-1] == g
        assert abs(approaching[-2] - g) < abs(approaching[0] - g)  # monotone approach


# --------------------------------------------------------------------------- #
# §7 — measurement-verification: PLACEBO + LOOK-AHEAD INJECTION                 #
# A self-contained look-ahead-safe position generator proves the t->t+1 time    #
# arrow is preserved in MECHANICS, not just in name.                            #
# --------------------------------------------------------------------------- #
def _synth_active(n_days: int = 240, seed: int = 7, *, placebo: bool = False,
                  leak: bool = False) -> np.ndarray:
    """Deterministic look-ahead-safe active-return series.

    signal_t is known at t; the forward return r_{t->t+1} carries a real (modest) edge
    on signal. Position at t = sign(signal_t) (look-ahead-safe). Active = pos * r.
      placebo: shuffle the realized returns independently of the signal -> edge dies.
      leak   : position PEEKS the realized forward return (sign(r)) -> time arrow broken
               -> active = |r|, grossly inflated.
    """
    rng = np.random.default_rng(seed)
    sig = rng.normal(0.0, 1.0, n_days)
    eps = rng.normal(0.0, 0.02, n_days)
    # A MODEST per-day edge (signal coeff << noise) so the look-ahead-safe build stays
    # small while a leak — which harvests the full |return| amplitude — dwarfs it.
    realized = 0.004 * sig + eps  # forward return depends on the (past-known) signal
    if placebo:
        realized = rng.permutation(realized)  # break signal<->return link
    pos = np.sign(realized) if leak else np.sign(sig)
    return pos * realized


def _gross(active: np.ndarray) -> float:
    return float(np.mean(active) * 252.0)


class TestPlaceboAndLookAhead:
    def test_real_edge_is_positive_but_modest(self):
        g = _gross(_synth_active())
        assert g > 0.0
        assert g < 1.5  # modest — not the absurd magnitude a leak would produce

    def test_placebo_collapses_relative_to_the_real_edge(self):
        # Shuffling returns vs signal must destroy the edge in BOTH layers (the ideal
        # layer cannot manufacture signal from noise): the placebo edge collapses to a
        # small fraction of the real look-ahead-safe edge.
        real = _gross(_synth_active())
        placebo = _gross(_synth_active(placebo=True))
        assert abs(placebo) < 0.5 * abs(real)
        rep = dual_layer_report(placebo, FrictionParams.null(), shared_position_fingerprint="p",
                                strong_ideal_ann=0.10, dead_realistic_band=0.0)
        assert rep.friction_grave_hint["candidate"] is False

    def test_look_ahead_injection_inflates_the_ideal_layer(self):
        # Breaking the time arrow (position peeks the realized return) must BALLOON the
        # ideal layer relative to the look-ahead-safe build. This proves the protection
        # is the TIME ARROW (preserved in both layers), not the friction knobs.
        safe = _gross(_synth_active(leak=False))
        leaked = _gross(_synth_active(leak=True))
        assert leaked > safe * 3.0  # a real leak is unmistakable
        rep_safe = dual_layer_report(safe, FrictionParams.null(), shared_position_fingerprint="s",
                                     strong_ideal_ann=0.10, dead_realistic_band=0.0)
        rep_leak = dual_layer_report(leaked, FrictionParams.null(), shared_position_fingerprint="l",
                                     strong_ideal_ann=0.10, dead_realistic_band=0.0)
        assert rep_leak.ideal.net_active_ann > rep_safe.ideal.net_active_ann * 3.0

    def test_position_fingerprint_is_deterministic_and_distinguishing(self):
        a = _synth_active(seed=7)
        assert position_fingerprint(a) == position_fingerprint(_synth_active(seed=7))  # stable
        assert position_fingerprint(a) != position_fingerprint(_synth_active(seed=8))  # sensitive


# --------------------------------------------------------------------------- #
# §1b/§4 — ADDITIVITY vs the committed harness: the layer reproduces the engine #
# gross/net UNCHANGED (proof the verdict layer numbers do not move).            #
# --------------------------------------------------------------------------- #
class _VecSignal:
    construction_window = 1

    def __init__(self, vec, names, name):
        import pandas as pd
        self.name = name
        self._s = pd.Series(np.asarray(vec, dtype=float), index=names)

    def scores(self, panel, names, asof):
        return self._s.reindex(names)


def _factor_panel(n_names=120, n_dates=300, seed=0):
    import pandas as pd
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2021-01-04", periods=n_dates)
    names = [f"S{i:03d}" for i in range(n_names)]
    mkt_ret = rng.normal(0.0, 0.01, size=n_dates)
    market = pd.Series(100.0 * np.cumprod(1.0 + mkt_ret), index=dates)
    beta = rng.uniform(0.4, 1.6, size=n_names)
    idio = rng.normal(0.0, 0.02, size=(n_dates, n_names))
    f = rng.normal(0.0, 1.0, size=n_names)
    f -= f.mean()
    daily = beta[None, :] * mkt_ret[:, None] + 0.0025 * f[None, :] + idio
    tr = pd.DataFrame(100.0 * np.cumprod(1.0 + daily, axis=0), index=dates, columns=names)
    value_tl = pd.DataFrame(np.tile(1e8 * (1.0 + np.arange(n_names) / n_names), (n_dates, 1)),
                            index=dates, columns=names)
    one = pd.Series(1.0, index=dates)
    panel = Panel(close=tr.copy(), tr_gross=tr, tr_net=tr, value_tl=value_tl, membership={},
                  market=market, tufe=one, tlref=one, frequency=Frequency.DAILY)
    return panel, f, names


class TestAdditivityVsHarness:
    def test_layer_reproduces_harness_gross_and_net(self):
        panel, sig, names = _factor_panel()
        out = harness(panel, _VecSignal(sig, names, "factor"),
                      SplitSpec(split_mode=SplitMode.NAME, frequency=Frequency.DAILY, seed=0),
                      DialConfig())
        rep = from_engine_output(out)
        # ideal recovers the harness GROSS (money-cost zeroed); realistic recovers the
        # harness NET (gross - cost - tax) — both UNCHANGED from the committed engine.
        assert rep.ideal.net_active_ann == out.gross_active_ann
        assert rep.realistic.net_active_ann == pytest.approx(out.net_active_ann)
        assert rep.differential_invariant_holds()

    def test_tradability_overlay_only_touches_realistic(self):
        panel, sig, names = _factor_panel()
        out = harness(panel, _VecSignal(sig, names, "factor"),
                      SplitSpec(split_mode=SplitMode.NAME, frequency=Frequency.DAILY, seed=0),
                      DialConfig())
        rep = from_engine_output(out, tradability=FrictionParams(fill_fraction=0.1,
                                                                 access_haircut_ann=0.05))
        assert rep.ideal.net_active_ann == out.gross_active_ann       # ideal still = gross
        assert rep.realistic.friction.fill_fraction == 0.1            # overlay on realistic only


# --------------------------------------------------------------------------- #
# §6 — SYNTHETIC IPO golden fixture (NON-VERDICT / SYNTHETIC-CALIBRATION).      #
# Byte-stable assert; MTH-golden analogue. NOT an IPO finding.                  #
# --------------------------------------------------------------------------- #
# Pre-registered (frozen BEFORE the numbers are read): the ideal layer shows the
# first-week-pop phenomenon (gross > 0); the realistic layer is killed to ~0/negative
# by the IPO tradability wall (allocation lottery + secondary ceiling-lock). The
# divergence IS the friction-grave concept, made concrete on synthetic inputs.
_IPO_GROSS_ANN = 0.40                       # synthetic "first-week pop", frictionless
_IPO_FRICTION = FrictionParams(
    cost_ann=0.015,          # commission + spread + impact
    tax_ann=0.0,
    fill_fraction=0.10,      # allocation lottery: 10% of the intended position fills
    access_haircut_ann=0.04, # secondary ceiling-lock: late, worse entry
)
# frozen golden outputs (recomputed by the same pure-arithmetic formula -> bit-stable)
_GOLDEN_IDEAL_NET = 0.40
_GOLDEN_REALISTIC_NET = apply_friction(_IPO_GROSS_ANN, _IPO_FRICTION)


class TestSyntheticIpoGoldenFixture:
    """SYNTHETIC-CALIBRATION, NON-VERDICT. Freezes the two-layer mechanics; it is not
    a measurement of any real IPO. Real-data n=24 validation is DEFERRED (see RR-Y1-027
    / RESEARCH_REGISTRY)."""

    def _rep(self) -> DualLayerReport:
        return dual_layer_report(
            _IPO_GROSS_ANN, _IPO_FRICTION,
            shared_position_fingerprint=position_fingerprint([_IPO_GROSS_ANN]),
            strong_ideal_ann=0.10, dead_realistic_band=0.0,
        )

    def test_preregistered_divergence(self):
        rep = self._rep()
        # ideal shows the phenomenon ...
        assert rep.ideal.net_active_ann == _GOLDEN_IDEAL_NET
        assert rep.ideal.net_active_ann > 0.10
        # ... realistic is killed to ~0 or negative by the tradability wall.
        assert rep.realistic.net_active_ann == _GOLDEN_REALISTIC_NET
        assert rep.realistic.net_active_ann <= 0.0

    def test_classified_as_friction_grave_candidate(self):
        h = self._rep().friction_grave_hint
        assert h["candidate"] is True
        assert h["tradability_bound"] is True
        assert h["requires_human"] is True

    def test_byte_stable(self):
        # MTH-golden analogue: same inputs -> bit-identical outputs, twice.
        a, b = self._rep().to_dict(), self._rep().to_dict()
        assert a == b
        # pinned literals (pure arithmetic, version-independent)
        assert round(_GOLDEN_REALISTIC_NET, 12) == -0.015
        assert self._rep().ideal.is_verdict is False  # the frozen number is NON-VERDICT
