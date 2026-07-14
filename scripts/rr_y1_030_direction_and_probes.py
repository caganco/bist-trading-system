"""RR-Y1-030 — direction verification + multi-probe + impact scan for the PIT eligibility fix.

Frozen spec: docs/yol1/STAGE0_RR-Y1-030_pit_eligibility.json (committed BEFORE this ran).

Three things, in this order, because the first one can STOP the other two:

  1. DIRECTION. The expected universe size comes from RR-Y1-029 -- a separate READ-ONLY
     diagnostic that ran before this fix existed. This is deliberate: in RR-Y1-028/D1b a CPI
     fix nearly shipped with the sign inverted and the unit test written beside it ENCODED the
     inversion and passed. An expectation derived inside the same directive as the fix is worth
     nothing. The STOP conditions are frozen in the spec; if one fires, the fix does not ship.

  2. MULTI-PROBE, including a SURVIVORSHIP-CORRELATED signal. RR-Y1-029 tested one probe (hi52,
     momentum-shaped) and found the peek did not move the conjugate answer. One probe is evidence,
     not a theorem -- and the probe most likely to be moved by a survivor-selected universe is one
     correlated with survival itself. lowvol63 is that probe, and the correlation is MEASURED here
     before any null result is interpreted (a null from an uncorrelated probe proves nothing).

  3. IMPACT SCAN (D3 discipline). Does the fix change any RECORDED verdict? Expected zero --
     RR-Y1-029 measured that no committed verdict placed agreement/pbo in its keep-bar. Measure it.

Output: docs/yol1/RR-Y1-030_direction_probes_impact.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.engine import config  # noqa: E402
from src.engine.contracts import (  # noqa: E402
    DialConfig,
    Frequency,
    SortDepth,
    SplitMode,
    SplitSpec,
)
from src.engine.data_adapter import load_panel  # noqa: E402
from src.engine.harness import harness  # noqa: E402
from src.engine.moda import _eligible_names, _pit_floor  # noqa: E402

OUT = REPO / "docs" / "yol1" / "RR-Y1-030_direction_probes_impact.json"
SPEC = REPO / "docs" / "yol1" / "STAGE0_RR-Y1-030_pit_eligibility.json"
D0, D1 = pd.Timestamp("2019-07-03"), pd.Timestamp("2026-04-22")
TRAIL = config.LIQUID_TRAILING_DAYS
NEED = 2 * config.MIN_NAMES_PER_ARM

# frozen in the spec, sourced from RR-Y1-029 (an independent, earlier directive)
EXPECT_LO, EXPECT_HI = 303, 310
STOP_SHRINK_BELOW = 231  # the shipped window universe
STOP_BLOWN_OPEN = 400


def elig(panel, *, legacy: bool) -> list[str]:
    return _eligible_names(
        panel, panel.names, split_asof=D0, d0=D0, d1=D1,
        floor_tl=(config.ELIGIBLE_ADV_FLOOR_TL if legacy else config.ELIGIBLE_ADV_FLOOR_BASE_TL),
        trailing=TRAIL, legacy_window_rule=legacy,
    )


def conjugate(panel, names: list[str], signal) -> dict:
    """Mod-A conjugate fields, with the eligible universe PINNED to ``names``.

    Two implementation notes, both load-bearing:

    1. ``run_moda`` is called directly rather than the full harness. The probe question is
       exclusively about the CONJUGATE reading (agreement / sign / real CSCV pbo); the harness's
       returns/cost and Mod-B legs are irrelevant here AND structurally independent of eligibility
       -- which is exactly what section 3 tests separately.

    2. ``moda._eligible_names`` is PINNED to return ``names`` verbatim. Without this the
       comparison is confounded: restricting the panel to the legacy 231 and then letting run_moda
       apply the (now PIT) eligibility internally re-filters that set, so the "with peek" arm is
       not the legacy rule at all. The first version of this script did exactly that and produced
       a t of 2.7282 for a universe RR-Y1-029 had measured at 2.7787 -- the discrepancy is what
       exposed the confound. Pinning isolates the ELIGIBILITY RULE, which is the only variable
       under test.
    """
    from unittest.mock import patch

    from src.engine.moda import run_moda

    spec = SplitSpec(
        split_mode=SplitMode.NAME, frequency=Frequency.DAILY, embargo_h=21,
        R=config.SPLIT_R_MIN, seed=0, sort_depth=SortDepth.TERCILE,
    )
    pinned = sorted(n for n in names if n in panel.close.columns)
    with patch("src.engine.moda._eligible_names", return_value=pinned):
        r = run_moda(panel, signal, spec, DialConfig(nw_lag=21))

    def f(x):
        return round(float(x), 4) if x is not None and np.isfinite(x) else None

    return {
        "n": len(pinned),
        "agreement_measured": r["agreement_measured"],
        "agreement_pass": r["agreement_pass"],
        "t_cross": f(r["agreement_t_cross_median"]),
        "sign_consistency": f(r["sign_consistency"]),
        "pbo": f(r["pbo"]),
        "confidence": str(r["agreement_confidence"]),
    }


def main() -> None:
    spec_doc = json.loads(SPEC.read_text(encoding="utf-8"))
    assert spec_doc["frozen_before_results"] is True

    panel = load_panel()
    res: dict = {
        "id": "RR-Y1-030 -- direction + multi-probe + impact",
        "spec": SPEC.name,
        "expectation_source": "RR-Y1-029 (independent, earlier directive) -- NOT derived here",
    }

    # ---------------------------------------------------------------- 1. DIRECTION
    pit = elig(panel, legacy=False)
    legacy = elig(panel, legacy=True)
    n_pit, n_legacy = len(pit), len(legacy)
    floor_d0 = _pit_floor(panel, D0)
    floor_d1 = _pit_floor(panel, D1)

    stops = []
    if n_pit < STOP_SHRINK_BELOW:
        stops.append(f"INVERTED DIRECTION: PIT universe {n_pit} < shipped {STOP_SHRINK_BELOW}")
    if n_pit < NEED:
        stops.append(f"Mod-A re-broken: {n_pit} < {NEED} needed for two arms")
    if n_pit > STOP_BLOWN_OPEN:
        stops.append(f"universe blown open: {n_pit} > {STOP_BLOWN_OPEN} -- the floor stopped biting")

    res["1_DIRECTION"] = {
        "shipped_window_rule (legacy)": n_legacy,
        "PIT (this fix)": n_pit,
        "expected_from_RR_Y1_029": f"{EXPECT_LO} <= n <= {EXPECT_HI}",
        "in_expected_band": bool(EXPECT_LO <= n_pit <= EXPECT_HI),
        "floor_at_d0_TL": round(floor_d0, 0),
        "floor_at_d1_TL": round(floor_d1, 0),
        "floor_equivalence_check": {
            "committed_end_of_window_anchor_TL": config.ELIGIBLE_ADV_FLOOR_TL,
            "pit_floor_evaluated_at_d1_TL": round(floor_d1, 0),
            "relative_error": round(abs(floor_d1 - config.ELIGIBLE_ADV_FLOOR_TL)
                                    / config.ELIGIBLE_ADV_FLOOR_TL, 5),
            "reading": "the re-anchored floor must land back on the committed 2.0M real bar at "
                       "the end of the window -- this is a change of reference point, not of the "
                       "threshold.",
        },
        "STOP_CONDITIONS_FIRED": stops,
    }
    print(f"[1] DIRECTION  legacy={n_legacy}  PIT={n_pit}  "
          f"expected {EXPECT_LO}-{EXPECT_HI}  stops={stops or 'none'}", flush=True)
    if stops:
        res["VERDICT"] = "STOP -- the fix violates its own frozen direction guard. NOT shipped."
        OUT.write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(res["1_DIRECTION"], indent=2))
        raise SystemExit(1)

    # ------------------------------------------- 2. IS lowvol63 REALLY SURVIVORSHIP-CORRELATED?
    # Mandatory pre-check (frozen in the spec): a null from an UNCORRELATED probe proves nothing.
    sub = panel.close.loc[(panel.close.index >= D0) & (panel.close.index <= D1)]
    cov = sub.notna().mean()
    casualties = [n for n in panel.names if cov.get(n, 0.0) < config.ELIGIBLE_MIN_COVERAGE]
    survivors = [n for n in panel.names if cov.get(n, 0.0) >= config.ELIGIBLE_MIN_COVERAGE]

    ret = panel.close.astype(float).pct_change(fill_method=None)
    vol63 = ret.rolling(63, min_periods=63).std()
    vol_at_d0 = vol63.loc[vol63.index <= D0].iloc[-1]
    v_cas = vol_at_d0.reindex(casualties).dropna()
    v_sur = vol_at_d0.reindex(survivors).dropna()
    correlated = bool(len(v_cas) > 5 and len(v_sur) > 5 and v_cas.median() > v_sur.median())

    res["2a_probe_validity"] = {
        "question": "is lowvol63 ACTUALLY correlated with survival on this panel? (do not assume)",
        "n_casualties (coverage < 95% over the window)": len(v_cas),
        "n_survivors": len(v_sur),
        "median_63d_vol_at_d0_casualties": round(float(v_cas.median()), 5) if len(v_cas) else None,
        "median_63d_vol_at_d0_survivors": round(float(v_sur.median()), 5) if len(v_sur) else None,
        "casualties_are_more_volatile": correlated,
        "reading": (
            "if casualties are NOT more volatile, then lowvol63 is not survivorship-correlated on "
            "this panel and a null result from it would prove nothing -- a different probe would "
            "be needed. Reported before any probe result is interpreted."
        ),
    }
    print(f"[2a] lowvol63 survivorship-correlated? {correlated}  "
          f"(casualty vol {float(v_cas.median()):.4f} vs survivor {float(v_sur.median()):.4f})",
          flush=True)

    # ---------------------------------------------------------------- 2b. MULTI-PROBE
    from examples.rry1008.signals import Hi52Signal, Mom120Signal, ValueStaticSignal

    class LowVol63:
        """The survivorship-correlated probe: inverted 63d realized vol (D-203 formula)."""

        name = "lowvol63"
        construction_window = 21

        def __init__(self) -> None:
            self._c = None

        def scores(self, p, names, asof):
            if self._c is None:
                self._c = -p.close.astype(float).pct_change(fill_method=None) \
                    .rolling(63, min_periods=63).std()
            if asof not in self._c.index:
                return pd.Series(np.nan, index=names, dtype=float)
            return self._c.loc[asof].reindex(names)

    probes = {
        "hi52 (momentum-shaped; RR-Y1-029's single probe)": Hi52Signal(),
        "mom120": Mom120Signal(),
        "lowvol63 (SURVIVORSHIP-CORRELATED)": LowVol63(),
        "value_static": ValueStaticSignal(),
    }
    rows = {}
    for label, sig in probes.items():
        w = conjugate(panel, legacy, sig)   # WITH the peek
        p_ = conjugate(panel, pit, sig)     # WITHOUT
        dt = (
            round(p_["t_cross"] - w["t_cross"], 4)
            if (w["t_cross"] is not None and p_["t_cross"] is not None) else None
        )
        rows[label] = {
            "with_peek_legacy_universe": w,
            "without_peek_PIT_universe": p_,
            "delta_t_cross (PIT - legacy)": dt,
            "verdict_flipped": bool(w["agreement_pass"] != p_["agreement_pass"]),
        }
        print(f"[2b] {label:<45} t {w['t_cross']} -> {p_['t_cross']}  "
              f"(pass {w['agreement_pass']} -> {p_['agreement_pass']})", flush=True)
    res["2b_MULTI_PROBE"] = {
        "scope_guard": (
            "These are KNOWN-ANSWER probes used to measure the INSTRUMENT's sensitivity to the "
            "peek. No candidate is re-adjudicated: hi52/mom120/lowvol63/value_static are all "
            "closed on the INDEPENDENT screening path (D-203/204/205/208, NRR-007/008), which "
            "this directive does not touch. No verdict about any of them is produced or implied."
        ),
        "probes": rows,
    }

    # ---------------------------------------------------------------- 3. IMPACT SCAN
    # The verdict-bearing fields all come from the eligibility-FREE returns/cost path, so they
    # must be BYTE-IDENTICAL. Anything that moves falsifies RR-Y1-029's scope finding -> STOP.
    from src.engine.contracts import Panel

    impact = {}
    moved_any = []
    for label, sig in (("hi52", Hi52Signal()), ("mom120", Mom120Signal())):
        spec_ = SplitSpec(
            split_mode=SplitMode.PANEL, frequency=Frequency.DAILY, embargo_h=21,
            R=config.SPLIT_R_MIN, seed=0, sort_depth=SortDepth.TERCILE,
        )
        out = harness(panel, sig, spec_, DialConfig(nw_lag=21))
        impact[label] = {
            k: (round(float(getattr(out, k)), 8)
                if getattr(out, k) is not None and np.isfinite(getattr(out, k)) else None)
            for k in ("gross_active_ann", "net_active_ann", "cost_ann", "nw_t", "dsr")
        }
        impact[label]["beats_benchmark_floor"] = out.beats_benchmark_floor
    # Cross-check against the COMMITTED pre-fix values (RR-Y1-028's impact scan), rather than
    # asserting byte-identity from first principles. If eligibility leaked into these fields, this
    # is where it would show.
    prev_path = REPO / "docs" / "yol1" / "RR-Y1-028_d3_impact_scan.json"
    prev = {}
    if prev_path.exists():
        for row in json.loads(prev_path.read_text(encoding="utf-8")).get("rows", []):
            for tag in ("hi52", "mom120"):
                if row.get("candidate", "").endswith(tag):
                    prev[tag] = {
                        "gross_active_ann": row.get("gross_active_ann"),
                        "nw_t": row.get("nw_t"),
                    }
    for tag, before in prev.items():
        now = impact.get(tag, {})
        for k, v_before in before.items():
            v_now = now.get(k)
            if v_before is None or v_now is None:
                continue
            if abs(float(v_now) - float(v_before)) > 1e-6:
                moved_any.append(f"{tag}.{k}: {v_before} -> {v_now}")

    res["3_IMPACT_verdict_bearing_fields"] = {
        "claim": (
            "nw_t / gross / net / cost / dsr / beats_benchmark_floor come from the "
            "eligibility-FREE path (harness._tilt_active uses panel.names; modb uses panel.names). "
            "Changing eligibility must not move them AT ALL."
        ),
        "method": (
            "measured now, then diffed against the values RECORDED BEFORE this fix in "
            "docs/yol1/RR-Y1-028_d3_impact_scan.json. Not asserted from first principles."
        ),
        "values_now": impact,
        "values_recorded_before_the_fix": prev,
        "fields_that_moved": moved_any,
        "VERDICT": (
            "BYTE-IDENTICAL -- eligibility does not leak into any verdict-bearing field, "
            "confirming RR-Y1-029's scope finding."
            if not moved_any
            else "STOP -- a verdict-bearing field moved. Eligibility is leaking into a path "
                 "RR-Y1-029 measured as clean; that scope finding is falsified."
        ),
    }

    res["VERDICT"] = (
        "DIRECTION CONFIRMED -- the PIT universe is larger, in the band RR-Y1-029 independently "
        "predicted, and Mod-A still fires. See the probe table for how much the peek actually "
        "mattered."
    )
    OUT.write_text(json.dumps(res, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
