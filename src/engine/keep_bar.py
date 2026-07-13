"""Keep-bar adjudication over an ``EngineOutput`` (RR-Y1-028, D1d).

ADDITIVE. The engine deliberately emits a Section-7 *vector*, not a pass/fail bit
(``contracts.EngineOutput``), and each directive has historically adjudicated that vector
itself. That left one rule un-enforced anywhere: **a gate that could not be measured is not
a gate that failed.**

Before RR-Y1-028 the Mod-A degenerate-universe guard wrote ``agreement_pass=False`` and a NaN
``pbo``. A consumer doing the natural thing --

    checks = {"agreement": bool(out.agreement_pass), "pbo": out.pbo <= 0.50, ...}

-- therefore recorded two FAILS for a leg that never executed. On the real BIST panel that leg
has, in practice, never executed at all, so every candidate ever run lost both gates for free.

This module is the single place that reads the tri-state honestly. It classifies each condition
as PASS / FAIL / NOT-MEASURED and refuses to fold the third into the second. A verdict is
KEEP only if every condition genuinely PASSed; a run with an unmeasured condition is
INCONCLUSIVE, never a KEEP and never a FAIL.

"Not detected" is not "does not exist" (ADR-0007).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

import numpy as np

from . import config
from .contracts import EngineOutput


class Outcome(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    NOT_MEASURED = "not_measured"  # the engine produced no value for this condition


class Verdict(StrEnum):
    KEEP = "keep"  # every condition measured AND passed
    DROP = "drop"  # at least one condition measured AND failed
    INCONCLUSIVE = "inconclusive"  # nothing failed, but >= 1 condition was never measured


@dataclass(frozen=True)
class KeepBar:
    """The frozen DEC-049 bar. Defaults come from ``config`` -- not invented here."""

    pbo_max: float = config.PBO_THRESHOLD  # 0.50
    dsr_min: float = config.DSR_MIN  # 0.95
    nw_t_min: float = config.AGREEMENT_CROSS_IC_T_MIN  # 2.0
    require_agreement: bool = True
    require_pbo: bool = True
    require_dsr: bool = True
    require_nw_t: bool = False  # headline tilt NW-t; off by default (Stage-0 opts in)
    require_net_active_positive: bool = True
    require_beats_benchmark_floor: bool = True


@dataclass(frozen=True)
class KeepBarResult:
    verdict: Verdict
    conditions: dict[str, Outcome]
    passed: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    not_measured: list[str] = field(default_factory=list)
    notes: tuple[str, ...] = ()

    @property
    def is_keep(self) -> bool:
        return self.verdict is Verdict.KEEP


def _tri(measured: bool | None, passed: bool | None) -> Outcome:
    """Tri-state reducer: an unmeasured condition NEVER becomes a FAIL."""
    if not measured or passed is None:
        return Outcome.NOT_MEASURED
    return Outcome.PASS if passed else Outcome.FAIL


def _finite(x: float | None) -> bool:
    return x is not None and bool(np.isfinite(x))


def adjudicate(out: EngineOutput, bar: KeepBar | None = None) -> KeepBarResult:
    """Adjudicate an ``EngineOutput`` against the frozen keep-bar, honestly.

    The whole point of this function is the ``NOT_MEASURED`` row: a condition the engine
    could not evaluate is reported as such and makes the verdict INCONCLUSIVE. It is never
    silently counted as a failure (which is what a bare ``bool(out.agreement_pass)`` does).
    """
    bar = bar or KeepBar()
    cond: dict[str, Outcome] = {}
    notes: list[str] = []

    if bar.require_agreement:
        # agreement_measured may be None on outputs produced before RR-Y1-028; treat a
        # missing flag as "measured" ONLY when a real verdict is present, so historical
        # objects keep their meaning instead of silently turning INCONCLUSIVE.
        measured = out.agreement_measured
        if measured is None:
            measured = out.agreement_pass is not None
            notes.append(
                "agreement_measured absent (pre-RR-Y1-028 output): inferred from "
                "agreement_pass is not None"
            )
        cond["agreement_pass"] = _tri(measured, out.agreement_pass)

    if bar.require_pbo:
        measured = out.pbo_measured
        if measured is None:
            measured = _finite(out.pbo)
        cond["pbo<=max"] = _tri(measured, _finite(out.pbo) and out.pbo <= bar.pbo_max)

    if bar.require_dsr:
        cond["dsr>=min"] = _tri(_finite(out.dsr), _finite(out.dsr) and out.dsr >= bar.dsr_min)

    if bar.require_nw_t:
        cond["|nw_t|>=min"] = _tri(
            _finite(out.nw_t), _finite(out.nw_t) and abs(out.nw_t) >= bar.nw_t_min
        )

    if bar.require_net_active_positive:
        cond["net_active_ann>0"] = _tri(
            _finite(out.net_active_ann), _finite(out.net_active_ann) and out.net_active_ann > 0.0
        )

    if bar.require_beats_benchmark_floor:
        cond["beats_benchmark_floor"] = _tri(
            out.beats_benchmark_floor is not None, out.beats_benchmark_floor
        )

    passed = [k for k, v in cond.items() if v is Outcome.PASS]
    failed = [k for k, v in cond.items() if v is Outcome.FAIL]
    not_measured = [k for k, v in cond.items() if v is Outcome.NOT_MEASURED]

    if failed:
        verdict = Verdict.DROP
    elif not_measured:
        verdict = Verdict.INCONCLUSIVE
        notes.append(
            f"INCONCLUSIVE, not DROP: {len(not_measured)} condition(s) produced no measurement "
            f"({', '.join(not_measured)}). An unmeasured gate is not a failed gate (ADR-0007)."
        )
    else:
        verdict = Verdict.KEEP

    return KeepBarResult(
        verdict=verdict,
        conditions=cond,
        passed=passed,
        failed=failed,
        not_measured=not_measured,
        notes=tuple(notes),
    )
