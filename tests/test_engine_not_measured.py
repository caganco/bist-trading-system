"""RR-Y1-028 (D1d) -- the Mod-A guard must EMIT 'not measured', not a false negative.

Companion to test_engine_keep_bar.py: that file pins how an output is ADJUDICATED; this one
pins what the engine EMITS when the Mod-A leg cannot run (degenerate universe -- too few
eligible names to form two arms).

Pre-RR-Y1-028 the guard wrote ``agreement_pass=False`` + ``AgreementConfidence.LOW``, so an
absent measurement looked exactly like an underpowered-but-real one.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.engine.contracts import (
    AgreementConfidence,
    DialConfig,
    Frequency,
    NameSplitMethod,
    Panel,
    SortDepth,
    SplitMode,
    SplitSpec,
)
from src.engine.moda import run_moda


class _StaticSignal:
    """Parameter-free scorer: a fixed per-name vector, same every date."""

    construction_window = 1

    def __init__(self, names: list[str]) -> None:
        self.name = "static"
        self._vec = pd.Series(np.linspace(1.0, 0.0, len(names)), index=names)

    def scores(self, panel: Panel, names: list[str], asof: pd.Timestamp) -> pd.Series:
        return self._vec.reindex(names)


def _thin_panel(n_names: int = 40, n_days: int = 400) -> Panel:
    """A universe too thin to form two arms of 50 -> the ELIGIBLE-NAMES guard must fire.

    40 names is deliberate: it clears MIN_NAMES_CROSS_SECTION (30), so evaluation dates DO
    exist and the run reaches the arm-formation check, which then fails (40 < 2*50). A
    smaller panel would trip the earlier cross-section-floor guard instead and would not
    exercise the path this module is about.
    """
    rng = np.random.default_rng(7)
    dates = pd.bdate_range("2020-01-01", periods=n_days)
    names = [f"N{i:02d}" for i in range(n_names)]
    px = pd.DataFrame(
        100.0 * np.exp(np.cumsum(rng.normal(0, 0.01, size=(n_days, n_names)), axis=0)),
        index=dates,
        columns=names,
    )
    val = pd.DataFrame(5e7, index=dates, columns=names)  # liquid; breadth is the binding limit
    mkt = pd.Series(100.0 * np.exp(np.cumsum(rng.normal(0, 0.008, n_days))), index=dates)
    lvl = pd.Series(np.linspace(100.0, 140.0, n_days), index=dates)
    return Panel(
        close=px, tr_gross=px, tr_net=px, value_tl=val, membership={},
        market=mkt, tufe=lvl, tlref=lvl, frequency=Frequency.DAILY,
    )


@pytest.fixture(scope="module")
def guarded_result() -> dict:
    panel = _thin_panel()
    spec = SplitSpec(
        split_mode=SplitMode.NAME,
        frequency=Frequency.DAILY,
        embargo_h=1,
        R=5,
        seed=0,
        sort_depth=SortDepth.TERCILE,
        name_split_method=NameSplitMethod.RANDOM,
    )
    return run_moda(panel, _StaticSignal(panel.names), spec, DialConfig())


class TestGuardEmitsNotMeasured:
    def test_agreement_pass_is_None_not_False(self, guarded_result):
        """THE regression: a leg that never ran must not report a verdict of False."""
        assert guarded_result["agreement_pass"] is None
        assert guarded_result["agreement_pass"] is not False

    def test_agreement_measured_flag_is_false(self, guarded_result):
        assert guarded_result["agreement_measured"] is False

    def test_confidence_is_not_measured_not_low(self, guarded_result):
        """LOW means 'an underpowered measurement was made'. Here NONE was made."""
        assert guarded_result["agreement_confidence"] is AgreementConfidence.NOT_MEASURED
        assert guarded_result["agreement_confidence"] is not AgreementConfidence.LOW

    def test_the_reason_is_carried_verbatim(self, guarded_result):
        """A reader must see WHY the leg never ran, not a synthetic 'arm=0 < 50' grade."""
        reasons = guarded_result["agreement_confidence_reasons"]
        assert reasons, "NOT_MEASURED must carry the guard reason(s)"
        assert any("eligible names" in r for r in reasons)
        assert guarded_result["guard_messages"] == reasons


class TestMeasuredPathUnchanged:
    """A universe that CAN form arms must still produce a real, boolean verdict."""

    def test_measured_run_reports_agreement_measured_true(self):
        panel = _thin_panel(n_names=140, n_days=500)
        spec = SplitSpec(
            split_mode=SplitMode.NAME,
            frequency=Frequency.DAILY,
            embargo_h=1,
            R=3,
            seed=0,
            sort_depth=SortDepth.TERCILE,
            name_split_method=NameSplitMethod.RANDOM,
        )
        r = run_moda(panel, _StaticSignal(panel.names), spec, DialConfig())
        assert r["agreement_measured"] is True
        assert isinstance(r["agreement_pass"], bool)
        assert r["agreement_confidence"] is not AgreementConfidence.NOT_MEASURED
