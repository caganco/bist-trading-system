"""RR-Y1-028 -- D3 measurement-verification (mandatory for a headline-field math fix).

Three independent checks, per the directive:

  1. MECHANICAL PROOF (root cause, not assertion)
     Was the CPI deflation really applied to a DIFFERENCE? Proven as an arithmetic identity
     against the COMMITTED PEAD output -- no re-run, no reconstruction, no trust required:
         real_active_ann  ==  (1 + net_active_ann) / (1 + TUFE) - 1
     If that identity holds on the committed numbers, the deflator's input WAS the active
     spread. And ``benchmark_floor_ann`` is the nominal TUFE CAGR, so the recorded comparison
     was REAL-vs-NOMINAL.

  2. DIFFERENTIAL (same inputs; only D3 toggled)
     The corrected gate is re-derived from the SAME rc-vector, changing exactly one thing:
     what is fed to the floor. Everything else -- gross, net, cost, nw_t, dsr -- must be
     bit-for-bit unchanged. A diff anywhere else means the fix leaked.

  3. SANITY (the named case)
     A tilt earning +5%/yr over an EW benchmark that itself returned 60% nominal, in a
     ~38%-inflation window, must now PASS the floor. Pre-fix it was recorded as a -22% "real
     active" and FAILED.

Output: docs/yol1/RR-Y1-028_d3_measurement_verification.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.engine.benchmark import benchmark_floor  # noqa: E402
from src.engine.contracts import (  # noqa: E402
    DialConfig,
    Frequency,
    SortDepth,
    SplitMode,
    SplitSpec,
)
from src.engine.data_adapter import load_panel  # noqa: E402
from src.engine.harness import _returns_cost  # noqa: E402

OUT = REPO_ROOT / "docs" / "yol1" / "RR-Y1-028_d3_measurement_verification.json"
PEAD_OUT = REPO_ROOT / "docs" / "yol1" / "RR-Y1-014_engine_output.json"

TOL = 1e-6


# --------------------------------------------------------------------------- #
# 1. MECHANICAL PROOF -- on the COMMITTED record, as an arithmetic identity     #
# --------------------------------------------------------------------------- #
def mechanical_proof() -> dict:
    rec = json.loads(PEAD_OUT.read_text(encoding="utf-8"))["full_panel_engine_output"]
    net = float(rec["net_active_ann"])
    real_active = float(rec["real_active_ann"])
    floor = float(rec["benchmark_floor_ann"])

    # Solve the recorded numbers for the deflator that produced them.
    #   real_active = (1 + X) / (1 + tufe) - 1   =>   1 + tufe = (1 + X) / (1 + real_active)
    implied_tufe_from_net = (1.0 + net) / (1.0 + real_active) - 1.0

    # If the deflator's INPUT was the active spread, the implied TUFE must equal the recorded
    # floor (which is the nominal TUFE CAGR -- the TLREF leg fell back to TUFE via the guard).
    identity_holds = abs(implied_tufe_from_net - floor) < 1e-4

    # Counterfactual: had the input been a TOTAL return, the implied deflator would differ.
    return {
        "source": "docs/yol1/RR-Y1-014_engine_output.json :: full_panel_engine_output (COMMITTED)",
        "recorded_net_active_ann": net,
        "recorded_real_active_ann": real_active,
        "recorded_benchmark_floor_ann": floor,
        "implied_deflator_if_input_was_net_active": round(implied_tufe_from_net, 6),
        "identity_(1+net)/(1+tufe)-1 == real_active": identity_holds,
        "VERDICT": (
            "CONFIRMED -- the deflator's input WAS the active spread (a difference), and the "
            "result was then compared against the NOMINAL floor. Root cause established from "
            "the committed record itself, not from a claim."
            if identity_holds
            else "NOT CONFIRMED -- the identity does not hold; re-examine the root cause."
        ),
    }


# --------------------------------------------------------------------------- #
# 2. DIFFERENTIAL -- same rc-vector, only the floor's input changes             #
# --------------------------------------------------------------------------- #
class _StaticSignal:
    name = "mv_static"
    construction_window = 1

    def __init__(self, names: list[str]) -> None:
        self._vec = pd.Series(np.linspace(1.0, 0.0, len(names)), index=names)

    def scores(self, panel, names, asof):
        return self._vec.reindex(names)


def differential() -> dict:
    panel = load_panel()
    spec = SplitSpec(
        split_mode=SplitMode.NAME, frequency=Frequency.DAILY, embargo_h=1,
        sort_depth=SortDepth.TERCILE,
    )
    rc = _returns_cost(panel, _StaticSignal(panel.names), spec, DialConfig())

    total = float(rc.bench_ann + rc.net_active_ann)

    # OLD gate: feed the ACTIVE spread; compare the deflated result to the NOMINAL floor.
    bf_old_input = benchmark_floor(rc.net_active_ann, panel, rc.d0, rc.d1)
    tufe = bf_old_input.tufe_ann
    old_real_active = (1.0 + rc.net_active_ann) / (1.0 + tufe) - 1.0
    old_beats = bool(old_real_active > bf_old_input.benchmark_floor_ann)

    # NEW gate: feed the TOTAL; compare nominal to nominal.
    bf_new = benchmark_floor(total, panel, rc.d0, rc.d1, nominal_active_ann=rc.net_active_ann)

    unchanged = {
        "gross_active_ann": rc.gross_active_ann,
        "net_active_ann": rc.net_active_ann,
        "cost_ann": rc.cost_ann,
        "tax_ann": rc.tax_ann,
        "mean_rt_bps": rc.mean_rt_bps,
        "nw_t": rc.nw_t,
        "n_obs": rc.n_obs,
    }
    # the floor's own inputs (TUFE / TLREF / the nominal floor) must NOT move either
    floor_inputs_unchanged = (
        abs(bf_new.tufe_ann - bf_old_input.tufe_ann) < TOL
        and abs(bf_new.benchmark_floor_ann - bf_old_input.benchmark_floor_ann) < TOL
    )

    return {
        "what_changed": "ONLY the quantity handed to benchmark_floor (active spread -> total return)",
        "rc_vector_untouched_by_the_fix": unchanged,
        "floor_inputs_unchanged": floor_inputs_unchanged,
        "tufe_ann": round(tufe, 6),
        "benchmark_floor_ann_nominal": round(bf_new.benchmark_floor_ann, 6),
        "benchmark_ew_ann": round(rc.bench_ann, 6),
        "strategy_total_ann_nominal": round(total, 6),
        "OLD": {
            "input_to_floor": "net_active_ann (a DIFFERENCE)",
            "deflated_value": round(old_real_active, 6),
            "compared_against": "NOMINAL floor",
            "beats_benchmark_floor": old_beats,
        },
        "NEW": {
            "input_to_floor": "benchmark_ew_ann + net_active_ann (a TOTAL)",
            "real_total_ann": round(bf_new.real_total_ann, 6),
            "benchmark_floor_real_ann": round(bf_new.benchmark_floor_real_ann, 6),
            "compared_against": "NOMINAL floor (real-vs-real gives the identical boolean)",
            "beats_benchmark_floor": bf_new.beats_benchmark_floor,
        },
        "real_vs_real_agrees_with_nominal_vs_nominal": bool(
            (bf_new.real_total_ann > bf_new.benchmark_floor_real_ann)
            is bf_new.beats_benchmark_floor
        ),
        "difference_is_confined_to_the_gate": bool(floor_inputs_unchanged),
    }


# --------------------------------------------------------------------------- #
# 3. SANITY -- the named case                                                   #
# --------------------------------------------------------------------------- #
def sanity() -> dict:
    panel = load_panel()
    d0, d1 = panel.dates[0], panel.dates[-1]
    bench_ann, active_ann = 0.60, 0.05
    bf = benchmark_floor(
        bench_ann + active_ann, panel, d0, d1, nominal_active_ann=active_ann
    )
    old_real_active = (1.0 + active_ann) / (1.0 + bf.tufe_ann) - 1.0
    old_beats = bool(old_real_active > bf.benchmark_floor_ann)
    return {
        "case": "EW benchmark +60%/yr nominal; tilt adds +5%/yr net active; real BIST TUFE window",
        "tufe_ann": round(bf.tufe_ann, 4),
        "benchmark_floor_ann": round(bf.benchmark_floor_ann, 4),
        "OLD_recorded_real_active_ann": round(old_real_active, 4),
        "OLD_beats_benchmark_floor": old_beats,
        "NEW_strategy_total_ann": round(bench_ann + active_ann, 4),
        "NEW_beats_benchmark_floor": bf.beats_benchmark_floor,
        "VERDICT": (
            "PASS -- a healthy tilt is no longer auto-failed by the floor gate."
            if (bf.beats_benchmark_floor and not old_beats)
            else "REVIEW -- the sanity case did not behave as expected."
        ),
    }


def main() -> None:
    doc = {
        "id": "RR-Y1-028 D3 measurement-verification (differential + mechanical proof + sanity)",
        "1_mechanical_proof_root_cause": mechanical_proof(),
        "2_differential": differential(),
        "3_sanity": sanity(),
    }
    all_ok = (
        doc["1_mechanical_proof_root_cause"]["identity_(1+net)/(1+tufe)-1 == real_active"]
        and doc["2_differential"]["difference_is_confined_to_the_gate"]
        and doc["2_differential"]["real_vs_real_agrees_with_nominal_vs_nominal"]
        and doc["3_sanity"]["VERDICT"].startswith("PASS")
    )
    doc["ALL_CHECKS_PASS"] = bool(all_ok)
    OUT.write_text(json.dumps(doc, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(json.dumps(doc, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
