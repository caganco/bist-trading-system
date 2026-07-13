"""RR-Y1-028 (D1d) -- an unmeasured gate is not a failed gate.

The regression this locks: the Mod-A degenerate-universe guard used to write
``agreement_pass=False``, so a leg that NEVER RAN was indistinguishable from one that ran
and failed. Every keep-bar consumer then counted the absence of a measurement as a failure,
and on the real BIST panel that leg has in practice never run -- so every candidate lost
that gate for free.

Two invariants are pinned here:
  1. NOT-MEASURED does NOT produce a FAIL (it produces INCONCLUSIVE).
  2. A genuinely measured FAIL is STILL a FAIL (the fix must not launder real negatives).
"""
from __future__ import annotations

import numpy as np
import pytest

from src.engine.contracts import AgreementConfidence, EngineOutput
from src.engine.keep_bar import KeepBar, Outcome, Verdict, adjudicate


def _clean_output(**over) -> EngineOutput:
    """An output where every keep-bar condition is measured and passing."""
    base = {
        "agreement_pass": True,
        "agreement_measured": True,
        "pbo": 0.10,
        "pbo_measured": True,
        "dsr": 0.99,
        "net_active_ann": 0.05,
        "beats_benchmark_floor": True,
    }
    base.update(over)
    return EngineOutput(**base)


class TestNotMeasuredIsNotAFail:
    def test_unmeasured_agreement_is_inconclusive_not_drop(self):
        """The D1d core: Mod-A never ran -> INCONCLUSIVE, and 'agreement_pass' is NOT in failed."""
        out = _clean_output(agreement_pass=None, agreement_measured=False)
        r = adjudicate(out)
        assert r.conditions["agreement_pass"] is Outcome.NOT_MEASURED
        assert "agreement_pass" not in r.failed
        assert "agreement_pass" in r.not_measured
        assert r.verdict is Verdict.INCONCLUSIVE
        assert not r.is_keep

    def test_unmeasured_pbo_is_not_a_fail(self):
        """A NaN pbo from the guard must not be read as 'pbo <= 0.50' either way."""
        out = _clean_output(pbo=float("nan"), pbo_measured=False)
        r = adjudicate(out)
        assert r.conditions["pbo<=max"] is Outcome.NOT_MEASURED
        assert r.failed == []
        assert r.verdict is Verdict.INCONCLUSIVE

    def test_the_real_bist_shape_is_inconclusive_not_drop(self):
        """The shape every committed engine run actually had: Mod-A guarded, PBO absent.

        Pre-fix this scored 2 automatic FAILs. It must now be INCONCLUSIVE on those two and
        adjudicate the rest on their merits.
        """
        out = _clean_output(
            agreement_pass=None,
            agreement_measured=False,
            pbo=float("nan"),
            pbo_measured=False,
            agreement_confidence=AgreementConfidence.NOT_MEASURED,
        )
        r = adjudicate(out)
        assert set(r.not_measured) == {"agreement_pass", "pbo<=max"}
        assert r.failed == []
        assert r.verdict is Verdict.INCONCLUSIVE


class TestMeasuredFailsStillFail:
    """The fix must not launder real negatives into 'inconclusive'."""

    def test_measured_agreement_false_is_a_fail(self):
        out = _clean_output(agreement_pass=False, agreement_measured=True)
        r = adjudicate(out)
        assert r.conditions["agreement_pass"] is Outcome.FAIL
        assert r.verdict is Verdict.DROP

    def test_measured_pbo_over_bar_is_a_fail(self):
        out = _clean_output(pbo=0.80, pbo_measured=True)
        r = adjudicate(out)
        assert r.conditions["pbo<=max"] is Outcome.FAIL
        assert r.verdict is Verdict.DROP

    def test_negative_net_active_is_a_fail(self):
        out = _clean_output(net_active_ann=-0.01)
        r = adjudicate(out)
        assert r.verdict is Verdict.DROP

    def test_a_fail_beats_a_not_measured(self):
        """DROP dominates INCONCLUSIVE: one real failure is decisive even if another
        condition was never measured."""
        out = _clean_output(
            agreement_pass=None, agreement_measured=False, net_active_ann=-0.01
        )
        r = adjudicate(out)
        assert r.verdict is Verdict.DROP
        assert r.failed == ["net_active_ann>0"]
        assert r.not_measured == ["agreement_pass"]


class TestKeep:
    def test_all_measured_and_passing_is_keep(self):
        r = adjudicate(_clean_output())
        assert r.verdict is Verdict.KEEP
        assert r.is_keep
        assert r.failed == [] and r.not_measured == []


class TestBackwardCompatibility:
    """Outputs produced BEFORE RR-Y1-028 carry no ``agreement_measured`` flag."""

    def test_legacy_output_with_real_verdict_is_still_adjudicated(self):
        """agreement_measured=None + agreement_pass=False -> a real measured FAIL, not a
        silent downgrade to INCONCLUSIVE."""
        out = _clean_output(agreement_pass=False, agreement_measured=None)
        r = adjudicate(out)
        assert r.conditions["agreement_pass"] is Outcome.FAIL
        assert r.verdict is Verdict.DROP
        assert any("pre-RR-Y1-028" in n for n in r.notes)

    def test_legacy_output_with_no_verdict_is_not_measured(self):
        out = _clean_output(agreement_pass=None, agreement_measured=None)
        r = adjudicate(out)
        assert r.conditions["agreement_pass"] is Outcome.NOT_MEASURED
        assert r.verdict is Verdict.INCONCLUSIVE


class TestBarComesFromConfig:
    def test_defaults_are_the_frozen_dec049_values(self):
        bar = KeepBar()
        assert bar.pbo_max == pytest.approx(0.50)
        assert bar.dsr_min == pytest.approx(0.95)

    def test_dsr_below_bar_fails(self):
        out = _clean_output(dsr=0.50)
        assert adjudicate(out).verdict is Verdict.DROP

    def test_nan_dsr_is_not_measured(self):
        out = _clean_output(dsr=float("nan"))
        r = adjudicate(out)
        assert r.conditions["dsr>=min"] is Outcome.NOT_MEASURED
        assert r.verdict is Verdict.INCONCLUSIVE
