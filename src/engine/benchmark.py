"""Real-return deflate + benchmark-floor (math-spec v1.1 Section 6).

Frozen rule (Section 6, recon Section 4):
- real-deflate: TUFE ALWAYS (CPI, TP.FG.J0, 2019+; finite throughout the panel).
- benchmark-floor: pre-2022-07 = TUFE-only; 2022-07+ = max(TUFE, TLREF).
- silent-NaN trap (d213 precedent): the clean TLREF series is NaN before
  2022-07. If the floor window would reach into that NaN region, DO NOT let the
  NaN silently collapse the ``max`` -- guard-RAISE (record the message) and fall
  back to TUFE-only for that window.

Both TUFE and TLREF are LEVEL/INDEX series (not rates), so the annualized
benchmark is a calendar-day CAGR between the window endpoints, looked up with
``Series.asof`` (robust to the snapshots keeping their own, possibly monthly,
index that is NOT reindexed onto the panel's trading days).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import config
from .contracts import Panel

# Julian year in calendar days -- the CAGR convention for the LEVEL series above.
# (config.TRADING_DAYS_YR is the SEPARATE 252-day axis used for return-series
# annualization; mixing the two would mis-scale the floor.)
_CALENDAR_DAYS_PER_YEAR = 365.25


@dataclass(frozen=True)
class BenchmarkFloor:
    """Section 7 benchmark-floor sub-vector (bullet 4).

    ``tlref_ann`` is None when TLREF did not enter the floor -- either the window
    predates the clean series (by design, no guard) or the silent-NaN guard
    fired and we fell back to TUFE-only (``guard_raised`` True). ``beats_*`` is
    None when the comparison is undefined (a non-finite return or floor).

    RR-Y1-028 (D3) -- WHAT IS JUDGED. ``beats_benchmark_floor`` compares the strategy's
    TOTAL nominal return against the nominal floor. It used to deflate the ACTIVE
    (excess-over-EW) return and compare that REAL spread against a NOMINAL floor -- two
    errors compounding, which made the gate effectively unpassable in a ~38%/yr-inflation
    window. ``real_active_ann`` is RETAINED (committed field; PEAD's output carries it) but
    it is a descriptive quantity, NOT the adjudicated one.
    """

    # --- the adjudicated quantities (D3) ---
    real_total_ann: float  # TUFE-deflated TOTAL return of the strategy
    benchmark_floor_ann: float  # nominal max(TUFE, TLREF)
    benchmark_floor_real_ann: float  # the same floor, deflated -- so real-vs-real is available
    beats_benchmark_floor: bool | None  # nominal TOTAL vs nominal floor (== real vs real)
    # --- descriptive ---
    real_active_ann: float  # RETAINED (D3): TUFE-deflated ACTIVE spread. NOT adjudicated.
    tufe_ann: float
    tlref_ann: float | None
    guard_raised: bool
    guard_messages: tuple[str, ...]


def _cagr(level: pd.Series, d0: pd.Timestamp, d1: pd.Timestamp) -> float:
    """Calendar-day CAGR of a LEVEL series between its asof-levels at d0 and d1.

    ``asof`` returns the last non-NaN level at or before each endpoint, so a
    monthly CPI series -- or a snapshot index that does not land exactly on the
    trading-day endpoints -- still resolves. A pre-start (or all-NaN) endpoint
    yields NaN, which propagates to a NaN CAGR; the caller reads NaN as
    'benchmark unavailable on this window'.
    """
    if len(level) == 0:
        return float("nan")
    lvl0 = float(level.asof(d0))
    lvl1 = float(level.asof(d1))
    days = (pd.Timestamp(d1) - pd.Timestamp(d0)).days
    if not (np.isfinite(lvl0) and np.isfinite(lvl1)) or lvl0 <= 0.0 or days <= 0:
        return float("nan")
    return float((lvl1 / lvl0) ** (_CALENDAR_DAYS_PER_YEAR / days) - 1.0)


def benchmark_floor(
    nominal_total_ann: float,
    panel: Panel,
    d0: pd.Timestamp,
    d1: pd.Timestamp,
    *,
    nominal_active_ann: float | None = None,
    tlref_from: str = config.BENCHMARK_TLREF_FROM,
) -> BenchmarkFloor:
    """The strategy's TOTAL return vs the frozen benchmark floor (Section 6).

    RR-Y1-028 (D3) -- MATHEMATICAL BUG FIX, declared explicitly per ADR-0005.

    This function used to receive the ANNUALIZED ACTIVE return (``tilt - EW-universe``, a
    DIFFERENCE) and do two things to it that do not follow:

        real_active = (1 + nominal_ACTIVE) / (1 + TUFE) - 1     # deflating a SPREAD
        beats       = real_active > max(TUFE, TLREF)            # REAL vs NOMINAL

    Deflation applies to levels, not to differences: inflation is common to both legs of
    ``tilt - benchmark`` and has already cancelled in the spread. Comparing the (wrongly)
    deflated spread against a nominal rate then demanded that a tilt beat its OWN benchmark
    by more than the inflation rate -- in the 2019-2026 window (TUFE ~38%/yr) an unpassable
    bar for any honest long-only strategy.

    The corrected gate judges the strategy's TOTAL nominal return
    (``EW-benchmark + net-active``) against the nominal floor, i.e. like against like. The
    real-vs-real comparison is algebraically identical and is exposed too
    (``real_total_ann`` vs ``benchmark_floor_real_ann``).

    ``nominal_active_ann`` is optional and purely descriptive: when supplied, the retained
    ``real_active_ann`` field is populated with the old quantity so historical outputs stay
    interpretable. It plays no part in the verdict.

    Never raises on a silent TLREF NaN: it records a guard message and falls back
    to TUFE-only (the d213-precedent silent-NaN trap).
    """
    messages: list[str] = []
    tlref_from_ts = pd.Timestamp(tlref_from)

    tufe_ann = _cagr(panel.tufe, d0, d1)
    if not np.isfinite(tufe_ann):
        messages.append(
            f"TUFE deflator unavailable on [{d0.date()}, {d1.date()}] "
            "-- real return and benchmark floor cannot be computed."
        )

    tlref_ann: float | None = None
    if d1 < tlref_from_ts:
        # whole window predates the clean TLREF series -> TUFE-only, BY DESIGN (no guard)
        pass
    elif d0 < tlref_from_ts:
        # window straddles the boundary: the pre-2022-07 TLREF is the silent NaN.
        # Do NOT fabricate a CAGR across it -- record the guard, fall back to TUFE.
        messages.append(
            f"TLREF floor window [{d0.date()}, {d1.date()}] straddles the "
            f"pre-{tlref_from} silent-NaN region (d213 precedent); "
            "floor falls back to TUFE-only for this window."
        )
    else:
        tl = _cagr(panel.tlref, d0, d1)
        if np.isfinite(tl):
            tlref_ann = tl
        else:
            messages.append(
                f"TLREF non-finite inside its eligible window "
                f"[{d0.date()}, {d1.date()}] (>= {tlref_from}); "
                "floor falls back to TUFE-only for this window."
            )

    floor_components: list[float] = [tufe_ann] if np.isfinite(tufe_ann) else []
    if tlref_ann is not None and np.isfinite(tlref_ann):
        floor_components.append(tlref_ann)
    benchmark_floor_ann = max(floor_components) if floor_components else float("nan")

    def _deflate(x: float) -> float:
        return (1.0 + x) / (1.0 + tufe_ann) - 1.0 if np.isfinite(tufe_ann) else float("nan")

    real_total_ann = _deflate(nominal_total_ann)
    benchmark_floor_real_ann = _deflate(benchmark_floor_ann)
    # RETAINED, descriptive only (D3): the old deflated-spread quantity. Never adjudicated.
    real_active_ann = (
        _deflate(nominal_active_ann) if nominal_active_ann is not None else float("nan")
    )

    # D3: like against like. nominal TOTAL vs nominal floor. (Deflating both sides by the
    # same TUFE is a monotone transform, so real-vs-real yields the identical boolean --
    # which is exactly what the old real-vs-NOMINAL comparison did not.)
    if np.isfinite(nominal_total_ann) and np.isfinite(benchmark_floor_ann):
        beats: bool | None = bool(nominal_total_ann > benchmark_floor_ann)
    else:
        beats = None

    return BenchmarkFloor(
        real_total_ann=real_total_ann,
        benchmark_floor_ann=benchmark_floor_ann,
        benchmark_floor_real_ann=benchmark_floor_real_ann,
        beats_benchmark_floor=beats,
        real_active_ann=real_active_ann,
        tufe_ann=tufe_ann,
        tlref_ann=tlref_ann,
        guard_raised=bool(messages),
        guard_messages=tuple(messages),
    )
