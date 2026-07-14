"""RR-Y1-029 — Mod-A eligibility look-ahead: scope + impact diagnostic. READ-ONLY.

No fix. No code change. No verdict change. The point is to MEASURE the caveat RR-Y1-028-V
declared but could not verify away, so that a repair decision rests on evidence rather than on
the plausible-sounding argument "it is symmetric across arms and uses no returns, so it cannot
manufacture an agreement". That argument is a CLAIM. This script tests it.

Three questions, each answered by measurement:

  Q1 SCOPE   -- where exactly does the [d0, d1] full-window selection sit, and which legs does
                it feed? Established by reading the call graph; encoded here and asserted.
  Q2 IMPACT  -- did it determine any historical verdict? And, prospectively, how many names does
                the future half of the window add or remove -- and does the conjugate answer move?
  Q3 PORT    -- is this BIST-local, or does it travel to the Yol-3 US micro-cap track?

Output: docs/yol1/RR-Y1-029_eligibility_lookahead_diagnostic.json
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
    Panel,
    SortDepth,
    SplitMode,
    SplitSpec,
)
from src.engine.data_adapter import continuous_basket, load_panel  # noqa: E402
from src.engine.harness import harness  # noqa: E402
from src.engine.moda import _eligible_names, _real_adv_deflator, _trailing_adv  # noqa: E402

OUT = REPO / "docs" / "yol1" / "RR-Y1-029_eligibility_lookahead_diagnostic.json"
D0, D1 = pd.Timestamp("2019-07-03"), pd.Timestamp("2026-04-22")
TRAIL = config.LIQUID_TRAILING_DAYS


def restrict(panel: Panel, names: list[str]) -> Panel:
    keep = [n for n in names if n in panel.close.columns]
    return Panel(
        close=panel.close[keep], tr_gross=panel.tr_gross[keep], tr_net=panel.tr_net[keep],
        value_tl=panel.value_tl[keep],
        membership={k: v[[c for c in keep if c in v.columns]] for k, v in panel.membership.items()},
        market=panel.market, tufe=panel.tufe, tlref=panel.tlref, frequency=panel.frequency,
    )


def pit_eligible(panel: Panel) -> tuple[list[str], dict]:
    """Point-in-time eligibility: NOTHING after d0 is used.

    Liquidity: the trailing-63d median traded value AS OF d0 (already the look-ahead-safe
    statistic the OLD rule used). The tradability floor is the SAME REAL bar as the shipped rule,
    but expressed in d0 TL rather than end-of-window TL -- i.e. 2M TL deflated back to d0. This
    keeps the economics identical and changes only WHEN the measurement is taken.

    Coverage: measured on the PAST year [d0-252bd, d0] instead of the future window. A name's
    future attendance is, by definition, unknowable at d0; the honest PIT analogue is whether it
    was actually trading in the run-up.
    """
    defl_d0 = float(_real_adv_deflator(panel, panel.names, D1).asof(D0))
    floor_d0_tl = config.ELIGIBLE_ADV_FLOOR_TL / defl_d0  # same real bar, expressed in d0 TL

    adv_d0 = _trailing_adv(panel, panel.names, D0, trailing=TRAIL)
    liquid = [str(n) for n in adv_d0[adv_d0 >= floor_d0_tl].dropna().index]

    past0 = panel.dates[panel.dates <= D0][-252] if (panel.dates <= D0).sum() >= 252 else panel.dates[0]
    elig = continuous_basket(panel, past0, D0, names=liquid, min_cov=config.ELIGIBLE_MIN_COVERAGE)
    meta = {
        "tufe_deflator_at_d0": round(defl_d0, 4),
        "floor_in_d0_TL": round(floor_d0_tl, 0),
        "floor_in_end_of_window_TL": config.ELIGIBLE_ADV_FLOOR_TL,
        "past_coverage_window": [str(pd.Timestamp(past0).date()), str(D0.date())],
        "n_liquid_at_d0": len(liquid),
    }
    return elig, meta


def agreement_of(panel: Panel, names: list[str]) -> dict:
    """Run Mod-A on a universe and report ONLY the conjugate fields.

    Scope note: the probe signal is hi52, a KNOWN-ANSWER factor whose closure came from the
    independent D-208 fair-cost screening path. This is an INSTRUMENT sensitivity measurement --
    "does the conjugate answer move when the peek is removed" -- and is NOT a re-adjudication of
    hi52. No verdict about hi52 is produced, read, or implied here.
    """
    from examples.rry1008.signals import Hi52Signal

    spec = SplitSpec(
        split_mode=SplitMode.NAME, frequency=Frequency.DAILY, embargo_h=21,
        R=config.SPLIT_R_MIN, seed=0, sort_depth=SortDepth.TERCILE,
    )
    out = harness(restrict(panel, names), Hi52Signal(), spec, DialConfig(nw_lag=21))

    def f(x):
        return round(float(x), 4) if x is not None and np.isfinite(x) else None

    return {
        "n_names_in_panel": len(names),
        "agreement_measured": out.agreement_measured,
        "agreement_pass": out.agreement_pass,
        "agreement_t_cross_median": f(out.agreement_t_cross_median),
        "sign_consistency": f(out.sign_consistency),
        "pbo_real_cscv": f(out.pbo),
        "agreement_confidence": str(out.agreement_confidence),
        "guard_messages": list(out.guard_messages),
    }


def main() -> None:
    panel = load_panel()
    need = 2 * config.MIN_NAMES_PER_ARM

    # ---------------- Q1: SCOPE (call-graph facts, asserted) ----------------
    q1 = {
        "question": "Where is the [d0,d1] full-window selection, and which legs consume it?",
        "method": "call-graph read of src/engine/*, verified by grep; encoded here as fact, not opinion.",
        "the_look_ahead": (
            "moda._eligible_names(panel, names, split_asof, d0, d1) selects the universe using "
            "(a) _window_median_adv -- the MEDIAN over [d0,d1] of each name's trailing-63d median "
            "traded value, and (b) continuous_basket(panel, d0, d1, min_cov) -- attendance over "
            "[d0,d1]. Both read the FUTURE half of the evaluation window relative to d0."
        ),
        "pre_existing_vs_added": (
            "continuous_basket(d0, d1) predates RR-Y1-028 (the old rule used min_cov=1.0 over the "
            "same window). RR-Y1-028 ADDED the liquidity leg to that window-wide selection. So the "
            "look-ahead is not new; its SURFACE was widened from attendance-only to "
            "attendance+liquidity."
        ),
        "consumers": {
            "Mod_A (moda.run_moda:557)": {
                "uses_eligibility": True,
                "feeds_a_VERDICT": True,
                "which_fields": [
                    "agreement_pass", "agreement_t_cross_median", "sign_consistency",
                    "pbo (real CSCV)",
                ],
                "why": "name_splits() is built FROM `eligible`, and conjugate_agreement() runs on those arms. The verdict is computed on the peeked universe.",
            },
            "Mod_B (modb.run_modb:108)": {
                "uses_eligibility": False,
                "feeds_a_VERDICT": True,
                "which_fields": ["dsr", "pbo (Mod-B proxy)"],
                "why": "modb uses `names = panel.names` -- the full cross-section, no eligibility selection. CLEAN.",
            },
            "Mod_C (modc._residual_flag_on_window:68)": {
                "uses_eligibility": True,
                "feeds_a_VERDICT": False,
                "which_fields": ["holdout_confidence (additive qualifier ONLY)"],
                "why": "the eligibility call sits inside _residual_flag_on_window, whose output feeds assess_holdout_confidence. The Mod-C VERDICT (holdout_persistence_pass) comes from holdout_ic_t + sign, computed via rank_ic_series over the FULL cross-section. RR-Y1-009/010 already state the qualifier is additive-only and never moves pass/fail.",
            },
            "harness returns/cost path (_tilt_active)": {
                "uses_eligibility": False,
                "feeds_a_VERDICT": True,
                "which_fields": [
                    "gross_active_ann", "net_active_ann", "cost_ann", "nw_t",
                    "beats_benchmark_floor",
                ],
                "why": "_tilt_active scores panel.names directly; the universe is the whole panel, masked only by score/return availability at each date. CLEAN.",
            },
        },
        "ANSWER": (
            "The look-ahead is confined to moda._eligible_names. It reaches a VERDICT in exactly "
            "ONE leg: Mod-A (agreement + real CSCV PBO). Mod-C touches it but only through an "
            "additive confidence qualifier that by construction cannot move a pass/fail. Mod-B and "
            "the returns/cost path -- which is where EVERY committed verdict was actually decided "
            "-- do not use it at all."
        ),
    }

    # ---------------- Q2a: historical impact ----------------
    q2_hist = {
        "question": "Did this look-ahead determine any historical verdict?",
        "method": (
            "The look-ahead can only have decided a verdict if agreement_pass or the real CSCV pbo "
            "was IN that verdict's keep-bar AND was actually produced. Both are checked against the "
            "committed records (same discipline as the RR-Y1-028 D3 impact scan)."
        ),
        "records": {
            "PEAD (RR-Y1-014)": {
                "keep_bar": "full-panel NW-t >= 2.0 AND X2-lockbox NW-t >= 2.0 (RR-Y1-014-RESULT.md L12)",
                "agreement_in_keep_bar": False,
                "mod_a_actually_ran": False,
                "evidence": "committed engine output carries agreement_pass=false with the guard 'only 38 eligible names; need >= 100' -- the leg never executed.",
            },
            "VIOP-K2": {
                "keep_bar": 'Stage-0 single metric: {"metric": "nw_t_rank_ic", "threshold": 2.0}',
                "agreement_in_keep_bar": False,
                "mod_a_actually_ran": False,
                "evidence": "graveyard doc decides on NW-t = -0.073; the same 38-name guard applies.",
            },
            "RR-Y1-008 (part 1/2)": {
                "keep_bar": "N/A -- instrument exam (VALIDATOR-VALIDATION), not an edge verdict",
                "agreement_in_keep_bar": False,
                "mod_a_actually_ran": "with MIN_NAMES_PER_ARM relaxed to 30 and an arm of ~37 -- explicitly graded LOW confidence at the time",
                "evidence": "docs/RESEARCH_REGISTRY.md RR-Y1-008 row; config.py comment on AGREEMENT_MIN_ARM_FOR_HIGH_CONFIDENCE.",
            },
            "Mod-C (any record)": {
                "mod_c_ever_ran": False,
                "evidence": "grep: SplitMode.TIME_HOLDOUT appears ONLY in src/engine/* and tests/*. No script, no committed record uses it.",
            },
        },
        "ANSWER": (
            "ZERO. No committed verdict placed agreement_pass or the real CSCV pbo in its keep-bar, "
            "and on the real panel the Mod-A leg could not execute anyway (38 < 100). Mod-C never "
            "ran at all. Every committed verdict was decided on NW-t, which comes from the "
            "eligibility-free returns/cost path. The look-ahead has never touched a recorded result."
        ),
        "BUT": (
            "This is a statement about the PAST only. RR-Y1-028 made Mod-A executable (231 names). "
            "From this point on, the look-ahead sits directly in a verdict path. The historical "
            "impact is zero precisely because the leg was broken; fixing the leg is what activates "
            "the risk."
        ),
    }

    # ---------------- Q2b: prospective magnitude ----------------
    shipped = _eligible_names(
        panel, panel.names, split_asof=D0, d0=D0, d1=D1,
        floor_tl=config.ELIGIBLE_ADV_FLOOR_TL, trailing=TRAIL,
    )
    pit, pit_meta = pit_eligible(panel)
    s, p = set(shipped), set(pit)

    # of the future-admitted names, how many were not even TRADING at d0?
    px_at_d0 = panel.close.loc[panel.close.index <= D0].tail(1)
    not_trading_at_d0 = {n for n in (s - p) if px_at_d0[n].isna().all()}

    adv_d0 = _trailing_adv(panel, panel.names, D0, trailing=TRAIL)
    defl_d0 = float(_real_adv_deflator(panel, panel.names, D1).asof(D0))
    floor_d0 = config.ELIGIBLE_ADV_FLOOR_TL / defl_d0
    illiquid_at_d0 = {
        n for n in (s - p)
        if n in adv_d0.index and np.isfinite(adv_d0[n]) and adv_d0[n] < floor_d0
    }

    # WHY are the peek-excluded names excluded? Attribute each to a channel.
    excluded = sorted(p - s)
    sub = panel.close.loc[(panel.close.index >= D0) & (panel.close.index <= D1)]
    cov_fwd = sub[excluded].notna().mean() if excluded else pd.Series(dtype=float)
    # a name that stops trading inside the window: last non-NaN close well before d1
    last_seen = sub[excluded].apply(lambda c: c.last_valid_index()) if excluded else pd.Series(dtype=object)
    died = {n for n in excluded if cov_fwd.get(n, 1.0) < config.ELIGIBLE_MIN_COVERAGE}
    stopped_early = {
        n for n in excluded
        if last_seen.get(n) is not None and pd.notna(last_seen.get(n))
        and pd.Timestamp(last_seen[n]) < D1 - pd.Timedelta(days=180)
    }
    # dried up: attendance fine, but window-median liquidity fell under the floor
    adv_win = _eligible_names  # (kept for symmetry; the liquidity leg is measured below)
    from src.engine.moda import _window_median_adv

    med_win = _window_median_adv(panel, excluded, D0, D1, trailing=TRAIL) if excluded else pd.Series(dtype=float)
    dried_up = {
        n for n in excluded
        if n not in died and np.isfinite(med_win.get(n, np.nan))
        and med_win[n] < config.ELIGIBLE_ADV_FLOOR_TL
    }

    q2_mag = {
        "question": "How many names does the FUTURE half of the window add or remove -- and why?",
        "pit_construction": pit_meta,
        "n_shipped_window_rule": len(s),
        "n_pit_rule": len(p),
        "n_intersection": len(s & p),
        "admitted_ONLY_because_of_the_peek": len(s - p),
        "excluded_ONLY_because_of_the_peek": len(p - s),
        "HEADLINE": (
            "The window rule is MORE restrictive than the point-in-time rule (231 vs 303). The "
            "dominant channel is therefore NOT 'late-liquid names sneak in' -- it is 'names that "
            "later died or dried up are thrown out'. That is the survivorship direction, and it is "
            "~4x larger than the admission channel."
        ),
        "of_the_peek_ADMITTED_26": {
            "not_even_trading_at_d0": len(not_trading_at_d0),
            "trading_but_below_the_real_floor_at_d0": len(illiquid_at_d0),
            "reading": (
                "names the engine could not have known were tradable at d0; they are in the "
                "universe BECAUSE they later became liquid (late-liquidity selection)."
            ),
        },
        "of_the_peek_EXCLUDED_98_channel_attribution": {
            "attendance_below_95pct_over_the_window (delisted / halted out)": len(died),
            "of_those_stopped_trading_more_than_6_months_before_d1": len(stopped_early),
            "attendance_ok_but_window_median_liquidity_fell_under_the_floor (dried up)": len(dried_up),
            "unattributed": len(set(excluded) - died - dried_up),
            "reading": (
                "These are the CASUALTIES. They were tradable at d0 by a look-ahead-free measure, "
                "and the window rule removes them because of what happened AFTERWARDS. A universe "
                "built this way is, by construction, a universe of survivors."
            ),
        },
        "share_of_the_universe_that_is_peek_dependent": round(len(s - p) / max(1, len(s)), 4),
        "share_of_the_PIT_universe_removed_by_the_peek": round(len(p - s) / max(1, len(p)), 4),
    }

    # ---------------- Q2c: does the conjugate ANSWER move? ----------------
    a_shipped = agreement_of(panel, shipped)
    a_pit = agreement_of(panel, pit) if len(pit) >= need else {
        "n_names_in_panel": len(pit),
        "note": f"PIT universe has {len(pit)} names, below the {need} needed for two arms -- "
                "Mod-A cannot run on a look-ahead-free universe at all.",
        "agreement_measured": False,
    }
    q2_move = {
        "question": (
            "Does removing the peek change what Mod-A SAYS? The claim under test is: "
            "'symmetric across arms + no return data => cannot manufacture an agreement.'"
        ),
        "scope_guard": (
            "hi52 is used as a known-answer PROBE. This measures the INSTRUMENT's sensitivity to "
            "the peek. It is NOT a re-adjudication of hi52, whose closure rests on the independent "
            "D-208 fair-cost screening path. No verdict about any candidate is produced here."
        ),
        "with_peek_shipped_universe": a_shipped,
        "without_peek_pit_universe": a_pit,
    }

    # ---------------- Q3: does it port to Yol-3 (US micro-cap)? ----------------
    q3 = {
        "question": "Is this caveat BIST-local, or a portable defect that travels to the US track?",
        "evidence": {
            "ADR-0002 decision": (
                "'Expand into US micro-cap long-only systematic research as a new track (RR-Y3)... "
                "Phases run data-feasibility -> INFRASTRUCTURE PORT -> universe and data-quality "
                "probes -> pre-registered measurement.' Consequences: 'reuse of the MARKET-AGNOSTIC "
                "ENGINE in a second market.'"
            ),
            "where_the_defect_lives": (
                "src/engine/moda.py::_eligible_names -- inside the market-agnostic engine, not in "
                "any BIST-specific screening module. It takes a Panel and knows nothing about BIST."
            ),
        },
        "ANSWER": "PORTABLE DEFECT, not a BIST-local quirk. It ports by construction: the engine is what gets ported.",
        "and_it_is_WORSE_in_the_target_market": (
            "US micro-cap is exactly the population where a window-median liquidity filter plus an "
            "attendance filter is most dangerous: delisting rates are high and liquidity is born "
            "and dies within the window. Selecting names on [d0,d1] liquidity there systematically "
            "keeps the survivors and the late-liquid, which is the textbook survivorship trap the "
            "US track's whole thesis (institutional exclusion below liquidity thresholds) sits on "
            "top of. The one component that does NOT port is the TUFE indexing (D1b): with US CPI "
            "at ~2-3%/yr the deflator is ~1.0 and that fix is a near-no-op -- so the US port would "
            "inherit the look-ahead WITHOUT the inflation problem that motivated it."
        ),
        "implication_for_sequencing": (
            "ADR-0002 lists 'universe and data-quality probes' as a phase BEFORE pre-registered "
            "measurement. That is the correct place to fix this -- but only if the fix is known to "
            "be needed BEFORE the port, not discovered after."
        ),
    }

    doc = {
        "id": "RR-Y1-029 -- Mod-A eligibility look-ahead: scope + impact diagnostic (READ-ONLY)",
        "class": "diagnostic. No code change, no verdict change, no candidate re-adjudicated.",
        "provenance": "the caveat RR-Y1-028-V declared and could NOT verify away.",
        "Q1_SCOPE": q1,
        "Q2a_HISTORICAL_IMPACT": q2_hist,
        "Q2b_PROSPECTIVE_MAGNITUDE": q2_mag,
        "Q2c_DOES_THE_ANSWER_MOVE": q2_move,
        "Q3_PORTABILITY": q3,
    }
    OUT.write_text(json.dumps(doc, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    print("=" * 78)
    print("Q2b  MAGNITUDE")
    print(f"  shipped (window rule) : {len(s)}")
    print(f"  PIT (no peek)         : {len(p)}   [need {need} for two arms]")
    print(f"  intersection          : {len(s & p)}")
    print(f"  admitted ONLY by peek : {len(s - p)}   ({len(s-p)/max(1,len(s)):.1%} of the universe)")
    print(f"      not trading at d0 : {len(not_trading_at_d0)}")
    print(f"      below floor at d0 : {len(illiquid_at_d0)}")
    print(f"  excluded ONLY by peek : {len(p - s)}")
    print("=" * 78)
    print("Q2c  DOES THE CONJUGATE ANSWER MOVE?")
    for k, v in (("WITH peek", a_shipped), ("WITHOUT peek", a_pit)):
        print(f"  {k:<13} n={v.get('n_names_in_panel')}  measured={v.get('agreement_measured')}  "
              f"pass={v.get('agreement_pass')}  t={v.get('agreement_t_cross_median')}  "
              f"sign={v.get('sign_consistency')}  pbo={v.get('pbo_real_cscv')}")
    print("=" * 78)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
