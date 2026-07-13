"""RR-Y1-028 / D1a-b-c -- the POST-FREEZE measurement of the recalibrated Mod-A universe.

Pre-registration: docs/yol1/STAGE0_RR-Y1-028_D1_universe_calibration.json -- committed BEFORE
this ran. The three constants (2M TL tradability floor, TUFE-indexed; 0.95 coverage; window-median
liquidity statistic) are fixed there with an ex-ante anchor for each, and they will NOT be
adjusted after this result. The pre-registration states explicitly: if the pool is still below
100 names, the calibration has FAILED and is reported as a failure -- the constants are not
loosened until the leg fires.

This script answers exactly two questions and asserts nothing else:
  1. Does the recalibrated eligibility admit >= 2 * MIN_NAMES_PER_ARM names? (i.e. can Mod-A run?)
  2. If it now runs, what does the conjugate leg actually SAY -- on a signal whose answer is
     already known from an independent path, so that a working leg is distinguishable from a
     leg that merely produces numbers?

Output: docs/yol1/RR-Y1-028_d1_calibration_result.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

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
from src.engine.moda import _eligible_names, _real_adv_deflator, _window_median_adv  # noqa: E402

OUT = REPO_ROOT / "docs" / "yol1" / "RR-Y1-028_d1_calibration_result.json"
PREREG = REPO_ROOT / "docs" / "yol1" / "STAGE0_RR-Y1-028_D1_universe_calibration.json"


def main() -> None:
    prereg = json.loads(PREREG.read_text(encoding="utf-8"))
    assert prereg["frozen_before_results"] is True
    fc = prereg["FROZEN_CONSTANTS"]
    # the code must be running the FROZEN constants, not something drifted
    assert config.ELIGIBLE_ADV_FLOOR_TL == fc["ELIGIBLE_ADV_FLOOR_TL_END_OF_WINDOW"]
    assert config.ELIGIBLE_MIN_COVERAGE == fc["ELIGIBLE_MIN_COVERAGE"]
    assert config.ELIGIBLE_ADV_FLOOR_TUFE_INDEXED == fc["ELIGIBLE_ADV_FLOOR_IS_TUFE_INDEXED"]

    panel = load_panel()
    d0 = pd.Timestamp("2019-07-03")  # the eval window the engine actually reached (guard message)
    d1 = pd.Timestamp("2026-04-22")
    need = 2 * config.MIN_NAMES_PER_ARM

    # D1b: the ADV series is deflated into end-of-window TL; the floor is FLAT in that unit.
    defl = _real_adv_deflator(panel, panel.names, d1)
    eligible = _eligible_names(
        panel, panel.names, split_asof=d0, d0=d0, d1=d1,
        floor_tl=config.ELIGIBLE_ADV_FLOOR_TL, trailing=config.LIQUID_TRAILING_DAYS,
    )
    adv = _window_median_adv(panel, panel.names, d0, d1, trailing=config.LIQUID_TRAILING_DAYS)
    held_adv = adv.reindex(eligible).dropna()

    can_run = len(eligible) >= need

    res: dict = {
        "id": "RR-Y1-028 D1a/b/c -- recalibrated Mod-A eligible universe (POST-FREEZE)",
        "prereg": PREREG.name,
        "frozen_constants_in_force": {
            "ELIGIBLE_ADV_FLOOR_TL_end_of_window": config.ELIGIBLE_ADV_FLOOR_TL,
            "TUFE_indexed": config.ELIGIBLE_ADV_FLOOR_TUFE_INDEXED,
            "ELIGIBLE_MIN_COVERAGE": config.ELIGIBLE_MIN_COVERAGE,
            "MIN_NAMES_PER_ARM_UNCHANGED": config.MIN_NAMES_PER_ARM,
        },
        "window": [str(d0.date()), str(d1.date())],
        "universe_size": len(panel.names),
        "tufe_deflator_to_end_of_window": {
            "at_window_start": round(float(defl.loc[defl.index >= d0].iloc[0]), 4),
            "at_window_end": round(float(defl.loc[defl.index <= d1].iloc[-1]), 4),
            "reading": (
                "TUFE(end)/TUFE(t): > 1 early (2019 TL bought more), 1.0 at the end. Early-window "
                "turnover is scaled UP so the early window is not penalised for the currency alone."
            ),
        },
        "adv_unit": "end-of-window TL (the floor is FLAT in this unit)",
        "names_needed_for_two_arms": need,
        "n_eligible": len(eligible),
        "MOD_A_CAN_RUN": bool(can_run),
        "eligible_adv_profile_tl": {
            "min": round(float(held_adv.min()), 0) if len(held_adv) else None,
            "median": round(float(held_adv.median()), 0) if len(held_adv) else None,
            "max": round(float(held_adv.max()), 0) if len(held_adv) else None,
        },
        "before_vs_after": {
            "old_rule_n_eligible": 38,
            "old_rule": "trailing ADV >= 10M TL at a SINGLE date (d0) AND min_cov=1.0",
            "new_rule": (
                f"window-median trailing ADV >= {config.ELIGIBLE_ADV_FLOOR_TL:,.0f} TL "
                f"(TUFE-indexed) AND coverage >= {config.ELIGIBLE_MIN_COVERAGE:.0%}"
            ),
        },
    }

    if not can_run:
        res["VERDICT"] = (
            "CALIBRATION FAILED -- the eligible pool is still below the arm-formation floor. "
            "Per the pre-registration, the constants are NOT loosened to force the leg to fire. "
            "A differently-argued anchor would need its own fresh freeze."
        )
        OUT.write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return

    # --- the leg now runs: does it SAY anything, or merely produce numbers? ---
    # Known-answer probe: hi52 is a graveyard factor whose burial came from an INDEPENDENT path
    # (D-208 fair-cost screening). Feeding it here does not re-adjudicate it; it tells us whether
    # a leg that finally executes emits a coherent conjugate reading at all.
    from examples.rry1008.signals import Hi52Signal

    spec = SplitSpec(
        split_mode=SplitMode.NAME, frequency=Frequency.DAILY, embargo_h=21,
        R=config.SPLIT_R_MIN, seed=0, sort_depth=SortDepth.TERCILE,
    )
    out = harness(panel, Hi52Signal(), spec, DialConfig(nw_lag=21))

    res["mod_a_first_real_execution"] = {
        "probe_signal": "hi52 (known-answer; burial came from the INDEPENDENT D-208 screening path)",
        "scope_note": (
            "This does NOT re-adjudicate hi52. It is an instrument check: a conjugate leg that "
            "has never once executed on real BIST data is now executing, and we report what it "
            "emits. Any edge reading here is out of scope and is NOT a verdict."
        ),
        "agreement_measured": out.agreement_measured,
        "agreement_pass": out.agreement_pass,
        "agreement_t_cross_median": (
            round(out.agreement_t_cross_median, 4)
            if out.agreement_t_cross_median is not None
            and np.isfinite(out.agreement_t_cross_median) else None
        ),
        "sign_consistency": (
            round(out.sign_consistency, 4)
            if out.sign_consistency is not None and np.isfinite(out.sign_consistency) else None
        ),
        "pbo_real_cscv": (
            round(out.pbo, 4) if out.pbo is not None and np.isfinite(out.pbo) else None
        ),
        "pbo_measured": out.pbo_measured,
        "agreement_confidence": str(out.agreement_confidence),
        "guard_messages": list(out.guard_messages),
    }
    res["VERDICT"] = (
        "CALIBRATION SUCCEEDED -- Mod-A is executable on real BIST data for the first time. "
        "agreement_pass and the real CSCV PBO are now MEASURED quantities rather than a guard. "
        "This is a FORWARD bar: no closed candidate is reopened by it (ADR-0007)."
    )

    OUT.write_text(json.dumps(res, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(json.dumps(res, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
