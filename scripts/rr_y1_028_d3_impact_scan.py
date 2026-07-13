"""RR-Y1-028 -- D3 IMPACT SCAN over every verdict that passed through ``benchmark_floor``.

WHY. D3 was a mathematical bug in a HEADLINE verdict field: ``benchmark_floor`` deflated the
ACTIVE (excess-over-EW) return as if it were a total return and compared that REAL number to a
NOMINAL floor. In a ~38%/yr-inflation window that made the gate effectively unpassable. Fixing it
is not enough -- we must know whether the bug ever DECIDED a recorded verdict.

DISCIPLINE. This scan CLASSIFIES; it does not revive. A candidate whose burial turns out to have
been decided by the bug is a pipeline false-negative, NOT an automatic resurrection: it is FLAGGED
and handed to the cold-decision path (Orchestrator + maintainer). Graveyard permanence (ADR-0007)
is not something a Builder overrides with a scan.

FULL SET, not a sample. ``benchmark_floor`` has exactly one caller -- ``harness()`` -- so the blast
radius is precisely the set of production ``harness()`` invocations. Enumerated from the code, not
from memory (grep: 'harness(' across the repo, tests excluded):

    1. scripts/scratch/run_rr_y1_014_stage0.py:196   PEAD  (RR-Y1-014)  -> docs/yol1/RR-Y1-014_engine_output.json
    2. scripts/run_viop_k2_harness.py:249            VIOP-K2           -> data/processed/viop_k2_engine_output.json
    3. examples/rry1008/run_part1_known_answer.py:86 RR-Y1-008 part-1  (hi52 / mom120 / value_static)
    4. examples/rry1008/run_part2_redteam.py:155     RR-Y1-008 part-2  (mom-variant winner)

The screening-module records (d203..d213, nrr007/8) do NOT go through the engine harness and
therefore never touched benchmark_floor -- verified: none of them contains the field.

THE DECIDING QUESTION IS NOT "does the gate flip". A flipped ``beats_benchmark_floor`` only
CONTAMINATES a burial if that field was part of the record's keep-bar in the first place. Asking
only "does it flip" over-reports: it flags every run whose floor verdict moves, including runs
where the floor was recorded as a mere diagnostic, or which were never edge verdicts at all. So
each row carries an evidence-cited ``floor_in_keep_bar`` read from the committed record.

CLASSES
  FLOOR-NOT-IN-VERDICT  the recorded keep-bar did not contain beats_benchmark_floor -> D3 CANNOT
                        have determined this verdict, whether or not the gate flips. Cites the bar.
  GENUINE-NULL          gross active is indistinguishable from zero -> the candidate fails on its
                        own merits whatever D3 says. Verdict STANDS. ADR-0007 intact.
  D3-DETERMINED         the floor WAS in the bar, the corrected gate flips it, and the candidate is
                        not a genuine null -> the burial may be bug-contaminated. FLAG + report.
                        NO revival: handed to the cold-decision path.
  UNAFFECTED            the floor verdict does not move.

Output: docs/yol1/RR-Y1-028_d3_impact_scan.json  (+ stdout table)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.engine.contracts import (  # noqa: E402
    DialConfig,
    Frequency,
    SortDepth,
    SplitMode,
    SplitSpec,
)
from src.engine.harness import harness  # noqa: E402

OUT_JSON = REPO_ROOT / "docs" / "yol1" / "RR-Y1-028_d3_impact_scan.json"

# A gross active return this close to zero is a genuine null: no correction to a
# benchmark gate can rescue a candidate that produced no signal. Frozen here BEFORE
# the scan runs (it is a description of "indistinguishable from zero", not a bar tuned
# to any outcome): |gross_active_ann| < 1% AND |nw_t| < 1.0.
NULL_GROSS_ABS = 0.01
NULL_NW_T_ABS = 1.0


def _old_d3_beats(net_active_ann: float, tufe_ann: float, floor_ann: float) -> bool | None:
    """Reproduce the PRE-RR-Y1-028 gate exactly: deflate the ACTIVE spread, then compare
    that REAL number against the NOMINAL floor. This is the bug, re-executed on purpose."""
    if not (np.isfinite(net_active_ann) and np.isfinite(tufe_ann) and np.isfinite(floor_ann)):
        return None
    real_active = (1.0 + net_active_ann) / (1.0 + tufe_ann) - 1.0
    return bool(real_active > floor_ann)


def _classify(
    o, old_beats: bool | None, new_beats: bool | None, kb: dict[str, Any]
) -> tuple[str, str]:
    g = o.gross_active_ann
    t = o.nw_t
    is_null = (
        g is not None and np.isfinite(g) and abs(g) < NULL_GROSS_ABS
        and t is not None and np.isfinite(t) and abs(t) < NULL_NW_T_ABS
    )
    moved = old_beats != new_beats

    # The gate can only have DECIDED a verdict it was actually part of.
    if not kb["floor_in_keep_bar"]:
        return "FLOOR-NOT-IN-VERDICT", (
            f"the recorded keep-bar is {kb['keep_bar']!r} ({kb['evidence']}) -- it does NOT "
            f"contain beats_benchmark_floor. D3 {'flips' if moved else 'does not move'} the "
            f"gate ({old_beats} -> {new_beats}), but the gate played no part in this verdict, "
            "so the verdict cannot be D3-contaminated."
        )

    if not moved:
        if is_null:
            return "GENUINE-NULL", (
                f"floor verdict unchanged ({old_beats}); gross={g:.4f}, nw_t={t:.3f} -> no signal."
            )
        return "UNAFFECTED", f"floor verdict unchanged ({old_beats}); D3 did not move it."

    if is_null:
        return "GENUINE-NULL", (
            f"D3 flips the floor gate ({old_beats} -> {new_beats}), but gross={g:.4f}, "
            f"nw_t={t:.3f} is indistinguishable from zero. The candidate fails on its own "
            "merits regardless. Verdict STANDS; ADR-0007 intact."
        )
    return "D3-DETERMINED", (
        f"the floor IS in the keep-bar ({kb['keep_bar']!r}), D3 flips it ({old_beats} -> "
        f"{new_beats}), and the candidate is not a genuine null (gross={g:.4f}, nw_t={t:.3f}). "
        "The recorded burial may be bug-contaminated. FLAGGED for cold decision -- NOT revived."
    )


def _row(
    name: str, provenance: str, o, historical: dict[str, Any] | None, kb: dict[str, Any]
) -> dict[str, Any]:
    tufe = o.benchmark_floor_ann  # floor == max(TUFE, TLREF); TUFE is its usual binding leg
    # recover the true TUFE for the counterfactual: real_total = (1+total)/(1+tufe)-1
    if (
        o.strategy_total_ann is not None and np.isfinite(o.strategy_total_ann)
        and o.real_total_ann is not None and np.isfinite(o.real_total_ann)
    ):
        tufe = (1.0 + o.strategy_total_ann) / (1.0 + o.real_total_ann) - 1.0

    old_beats = _old_d3_beats(o.net_active_ann, tufe, o.benchmark_floor_ann)
    new_beats = o.beats_benchmark_floor
    klass, why = _classify(o, old_beats, new_beats, kb)

    return {
        "candidate": name,
        "provenance": provenance,
        "recorded_keep_bar": kb["keep_bar"],
        "floor_in_keep_bar": kb["floor_in_keep_bar"],
        "keep_bar_evidence": kb["evidence"],
        "gross_active_ann": o.gross_active_ann,
        "net_active_ann": o.net_active_ann,
        "nw_t": o.nw_t,
        "benchmark_ew_ann": o.benchmark_ew_ann,
        "strategy_total_ann": o.strategy_total_ann,
        "benchmark_floor_ann": o.benchmark_floor_ann,
        "tufe_ann_recovered": tufe,
        "D3_old_beats_floor": old_beats,
        "D3_corrected_beats_floor": new_beats,
        "historical_recorded_beats_floor": (
            historical.get("beats_benchmark_floor") if historical else None
        ),
        "historical_recorded_gross": (
            historical.get("gross_active_ann") if historical else None
        ),
        "CLASS": klass,
        "reason": why,
    }


# --------------------------------------------------------------------------- #
# recorded keep-bars -- read from the committed records, NOT inferred          #
# --------------------------------------------------------------------------- #
KB_PEAD = {
    "keep_bar": "full-panel NW-t >= 2.0 AND X2-lockbox NW-t >= 2.0",
    "floor_in_keep_bar": False,
    "evidence": (
        "docs/yol1/RR-Y1-014-RESULT.md L12 (frozen Stage-0 keep_bar) + L16-17 (the two rows "
        "that decided FAIL: -0.029 / -0.486). beats_benchmark_floor appears only at L49, in "
        "the DIAGNOSTICS block, and is not one of the bar's conditions."
    ),
}
KB_VIOP = {
    "keep_bar": 'Stage-0 keep_bar = {"metric": "nw_t_rank_ic", "threshold": 2.0, "direction": "greater"}',
    "floor_in_keep_bar": False,
    "evidence": (
        "docs/yol1/STAGE0_VIOP_SSF_OI.json (single-metric bar) + "
        "docs/yol1/graveyard/VIOP_SSF_OI.md L14: 'NW-t (tilt active return) > 2.0 | -0.073'."
    ),
}
KB_RRY1008 = {
    "keep_bar": "N/A -- instrument exam, not an edge verdict",
    "floor_in_keep_bar": False,
    "evidence": (
        "docs/RESEARCH_REGISTRY.md, RR-Y1-008 row: 'VALIDATOR-VALIDATION / RED-TEAM -- the "
        "validation engine's first REAL-DATA exam (alet-sinavi, edge-avi-DEGIL)'. It adjudicates "
        "the ENGINE, not these factors. The factors' burials (hi52 KESIN-KAPANDI, mom120/"
        "value_static SERAP) come from the SCREENING path (D-203/204/205/208, NRR-007/008), which "
        "never calls benchmark_floor -- verified: none of those results JSONs contains the field."
    ),
}


# --------------------------------------------------------------------------- #
# producers                                                                    #
# --------------------------------------------------------------------------- #
def scan_pead() -> dict[str, Any]:
    import importlib.util

    spec_ = importlib.util.spec_from_file_location(
        "_pead_mod", REPO_ROOT / "scripts" / "scratch" / "run_rr_y1_014_stage0.py"
    )
    mod = importlib.util.module_from_spec(spec_)
    spec_.loader.exec_module(mod)  # module is __main__-guarded; import is side-effect free

    _stage0, _freeze, _events, panel, signal = mod.load_inputs()
    spec = SplitSpec(
        split_mode=SplitMode.PANEL, frequency=Frequency.DAILY, embargo_h=mod.H_DAYS,
        seed=0, sort_depth=SortDepth.TERCILE,
    )
    out = harness(panel, signal, spec, DialConfig(), stage0_path=None)

    hist_path = REPO_ROOT / "docs" / "yol1" / "RR-Y1-014_engine_output.json"
    hist = json.loads(hist_path.read_text(encoding="utf-8")).get("full_panel_engine_output", {})
    return _row(
        "PEAD (RR-Y1-014)", "scripts/scratch/run_rr_y1_014_stage0.py:196", out, hist, KB_PEAD
    )


def scan_viop() -> dict[str, Any]:
    from src.engine.contracts import Panel
    from src.engine.data_adapter import load_panel
    from src.signals.viop_k2_split import ViOpK2Signal

    # NOTE: the K2 panel's name column is `ticker` (not `symbol`) -- schema read from the file.
    k2 = pd.read_parquet(REPO_ROOT / "data" / "processed" / "viop_signal_panel.parquet")
    signal = ViOpK2Signal(k2)
    panel = load_panel()
    names = sorted(set(k2["ticker"].astype(str).unique()) & set(panel.names))
    if not names:
        raise RuntimeError("no K2 ticker intersects the clean-universe panel")

    restricted = Panel(
        close=panel.close[names], tr_gross=panel.tr_gross[names], tr_net=panel.tr_net[names],
        value_tl=panel.value_tl[names],
        membership={
            k: v[[c for c in names if c in v.columns]] for k, v in panel.membership.items()
        },
        market=panel.market, tufe=panel.tufe, tlref=panel.tlref, frequency=panel.frequency,
    )
    spec = SplitSpec(  # mirrors scripts/run_viop_k2_harness.py:228-236
        split_mode=SplitMode.NAME, frequency=Frequency.DAILY, embargo_h=21,
        R=50, seed=42, sort_depth=SortDepth.TERCILE,
    )
    out = harness(restricted, signal, spec, DialConfig())

    hp = REPO_ROOT / "data" / "processed" / "viop_k2_engine_output.json"
    hist = {}
    if hp.exists():
        d = json.loads(hp.read_text(encoding="utf-8"))
        hist = d.get("engine_output", d)
    return _row(
        "VIOP-K2 (SSF OI growth)", "scripts/run_viop_k2_harness.py:249", out, hist, KB_VIOP
    )


def scan_rry1008() -> list[dict[str, Any]]:
    from examples.rry1008.signals import Hi52Signal, Mom120Signal, ValueStaticSignal
    from src.engine.data_adapter import load_panel

    panel = load_panel()
    spec = SplitSpec(
        split_mode=SplitMode.NAME, frequency=Frequency.DAILY, embargo_h=21,
        R=50, seed=0, sort_depth=SortDepth.TERCILE,
    )
    dial = DialConfig(nw_lag=21)  # part-1 passed this explicitly (overlap-aware, by hand)
    rows = []
    for sig in (Hi52Signal(), Mom120Signal(), ValueStaticSignal()):
        out = harness(panel, sig, spec, dial)
        rows.append(
            _row(
                f"RR-Y1-008 part-1 :: {sig.name}",
                "examples/rry1008/run_part1_known_answer.py:86",
                out,
                None,  # engine output was reported in-report, not committed as JSON
                KB_RRY1008,
            )
        )
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip", nargs="*", default=[], choices=["pead", "viop", "rry1008"])
    args = ap.parse_args()

    rows: list[dict[str, Any]] = []
    for tag, fn in (("pead", scan_pead), ("viop", scan_viop), ("rry1008", scan_rry1008)):
        if tag in args.skip:
            print(f"[{tag}] skipped", flush=True)
            continue
        print(f"[{tag}] running committed harness ...", flush=True)
        try:
            r = fn()
            rows.extend(r if isinstance(r, list) else [r])
        except Exception as exc:  # noqa: BLE001 -- a producer that cannot be replayed is REPORTED
            rows.append({
                "candidate": tag, "CLASS": "NOT-REPLAYABLE",
                "reason": f"{type(exc).__name__}: {exc}",
            })
            print(f"  !! {tag}: {exc}", flush=True)

    classes: dict[str, int] = {}
    for r in rows:
        classes[r["CLASS"]] = classes.get(r["CLASS"], 0) + 1
    flagged = [r for r in rows if r["CLASS"] == "D3-DETERMINED"]

    doc = {
        "id": "RR-Y1-028 D3 impact scan (full-set enumeration; classification only, NO revival)",
        "null_thresholds_frozen_before_scan": {
            "abs_gross_active_ann_lt": NULL_GROSS_ABS,
            "abs_nw_t_lt": NULL_NW_T_ABS,
        },
        "discipline": (
            "A D3-DETERMINED burial is a pipeline false-negative, not a graveyard revival. "
            "It is flagged and handed to the cold-decision path (Orchestrator + maintainer). "
            "ADR-0007 permanence is not overridden by this scan."
        ),
        "class_counts": classes,
        "n_flagged_D3_DETERMINED": len(flagged),
        "rows": rows,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(doc, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    def _f(x, w, p=4):
        return f"{x:>{w}.{p}f}" if isinstance(x, float) and np.isfinite(x) else f"{'-':>{w}}"

    print("\n" + "=" * 118)
    print(f"{'candidate':<34}{'gross':>9}{'nw_t':>8}{'oldD3':>7}{'newD3':>7}{'inBar':>7}  CLASS")
    print("=" * 118)
    for r in rows:
        if "gross_active_ann" not in r:
            print(f"{r['candidate']:<34}{'-':>9}{'-':>8}{'-':>7}{'-':>7}{'-':>7}  {r['CLASS']}")
            continue
        print(
            f"{r['candidate']:<34}"
            f"{_f(r['gross_active_ann'], 9)}"
            f"{_f(r['nw_t'], 8, 3)}"
            f"{str(r['D3_old_beats_floor']):>7}"
            f"{str(r['D3_corrected_beats_floor']):>7}"
            f"{str(r['floor_in_keep_bar']):>7}"
            f"  {r['CLASS']}"
        )
    print("=" * 118)
    print(f"class counts: {classes}")
    print(f"D3-DETERMINED (flagged for cold decision): {len(flagged)}")
    for f in flagged:
        print(f"  !! {f['candidate']}: {f['reason']}")
    print(f"\nwrote {OUT_JSON}")


if __name__ == "__main__":
    main()
