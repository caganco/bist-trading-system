# RR-Y1-029 — Mod-A eligibility look-ahead: scope + impact diagnostic

**Class:** diagnostic. **READ-ONLY** — no code change, no verdict change, no candidate
re-adjudicated. Machine-readable companion: `docs/yol1/RR-Y1-029_eligibility_lookahead_diagnostic.json`.

**Provenance.** RR-Y1-028-V declared a caveat it could not verify away: *"Mod-A eligibility is
computed over the FULL evaluation window [d0, d1]… applied symmetrically to both arms and uses no
return data, so it cannot by itself manufacture a conjugate agreement — but it is a real property
of the design and is reported as a CAVEAT, not verified away."*

That sentence contains a **claim** ("cannot manufacture an agreement"). This report measures it
instead of repeating it — and measures the scope and the blast radius around it. **No repair is
made here.** The D1b lesson applies: a fix whose *direction* was not measured first nearly shipped
inverted. Scope first, then a separate ex-ante spec.

---

## Q1 — SCOPE: where is the look-ahead, and which legs does it feed?

The look-ahead is confined to one function: `moda._eligible_names(panel, names, split_asof, d0, d1)`.
It selects the universe using **(a)** `_window_median_adv` — the median over `[d0, d1]` of each
name's trailing-63d median traded value — and **(b)** `continuous_basket(panel, d0, d1, min_cov)` —
attendance over `[d0, d1]`. Both read the **future half** of the evaluation window relative to `d0`.

> **Not new.** `continuous_basket(d0, d1)` predates RR-Y1-028: the old rule already required
> `min_cov = 1.0` over the same window. RR-Y1-028 **added the liquidity leg** to that window-wide
> selection. The look-ahead's *surface* widened from attendance-only to attendance + liquidity; the
> look-ahead itself was already there.

| leg | uses eligibility? | reaches a **verdict**? | which fields |
|---|:--:|:--:|---|
| **Mod-A** (`moda.run_moda:557`) | **yes** | **YES** | `agreement_pass`, `agreement_t_cross_median`, `sign_consistency`, real CSCV `pbo` |
| **Mod-B** (`modb.run_modb:108`) | no — uses `panel.names` | yes | `dsr`, proxy `pbo` — **clean** |
| **Mod-C** (`modc._residual_flag_on_window:68`) | yes | **NO** | only `holdout_confidence`, an *additive* qualifier |
| **harness returns/cost** (`_tilt_active`) | no — uses `panel.names` | yes | `gross/net_active_ann`, `cost_ann`, `nw_t`, `beats_benchmark_floor` — **clean** |

**Answer.** It reaches a verdict in **exactly one leg: Mod-A**. Mod-C touches the same helper, but
only through the confidence qualifier, which RR-Y1-009/010 define as additive-only and which by
construction never moves a pass/fail. **Mod-B and the returns/cost path — which is where every
committed verdict was actually decided — do not use it at all.**

---

## Q2a — HISTORICAL IMPACT: did it ever decide a verdict?

The look-ahead can only have decided a verdict if `agreement_pass` or the real CSCV `pbo` was
**in that verdict's keep-bar** *and* **was actually produced**. Both were checked against the
committed records (same discipline as the RR-Y1-028 D3 impact scan).

| record | keep-bar | agreement in bar? | Mod-A actually ran? |
|---|---|:--:|:--:|
| PEAD (RR-Y1-014) | full-panel NW-t ≥ 2.0 **and** X2-lockbox NW-t ≥ 2.0 | **no** | **no** — guard: *"only 38 eligible names; need ≥ 100"* |
| VIOP-K2 | Stage-0 single metric `nw_t_rank_ic ≥ 2.0` | **no** | **no** — same guard |
| RR-Y1-008 | N/A — instrument exam, not an edge verdict | **no** | with the arm floor relaxed to 30 (~37/arm), graded **LOW** confidence at the time |
| any Mod-C run | — | — | **Mod-C never ran**: `SplitMode.TIME_HOLDOUT` appears only in `src/engine/*` and `tests/*` |

### **ZERO.**

No committed verdict placed `agreement_pass` or the real CSCV `pbo` in its keep-bar, and on the
real panel the Mod-A leg could not execute anyway (38 < 100). Every committed verdict was decided
on **NW-t**, which comes from the eligibility-free returns/cost path.

> **But this is a statement about the past only.** RR-Y1-028 made Mod-A executable (231 names).
> **From now on the look-ahead sits directly in a verdict path.** The historical impact is zero
> *precisely because the leg was broken* — fixing the leg is what activates the risk.

---

## Q2b — PROSPECTIVE MAGNITUDE: how much of the universe is peek-dependent?

Point-in-time (PIT) comparison: liquidity measured on the trailing-63d window **as of d0** against
the *same real bar* (2M TL deflated back to d0 TL), and coverage measured on the **past** year
`[d0−252bd, d0]` instead of the future window. Nothing after `d0` is used.

```
shipped (window rule) : 231
PIT (no peek)         : 303        <-- MORE names, not fewer
intersection          : 205
admitted ONLY by peek :  26   (11.3% of the shipped universe)
excluded ONLY by peek :  98   (32.3% of the PIT universe)
```

**The headline is the opposite of the intuition.** The window rule is **more restrictive** than the
PIT rule. The dominant channel is therefore *not* "late-liquid names sneak in" — it is **"names
that later died or dried up are thrown out."** That is the **survivorship** direction, and it is
~4× larger than the admission channel.

### Full attribution of the 98 exclusions (nothing unattributed)

| channel | names |
|---|---:|
| attendance < 95% over the window — **delisted / halted out** | **39** |
| …of which stopped trading > 6 months before `d1` | 30 |
| attendance fine, but window-median liquidity fell under the floor — **dried up** | **59** |
| unattributed | **0** |

These are the **casualties**. They were tradable at `d0` by a look-ahead-free measure, and the
window rule removes them because of *what happened afterwards*. **A universe built this way is,
by construction, a universe of survivors.**

The 26 admissions are the mirror image: 23 were trading but **below** the real floor at `d0`
(they became liquid later), and 1 was not trading at all.

---

## Q2c — Does the conjugate ANSWER actually move?

The claim under test: *"symmetric across arms + no return data ⇒ cannot manufacture an agreement."*

Probe: `hi52` — a **known-answer** factor whose closure came from the *independent* D-208 fair-cost
screening path. **This is an instrument-sensitivity measurement, not a re-adjudication of hi52.**
No verdict about any candidate is produced, read, or implied.

| | n | measured | pass | t_cross | sign | real PBO |
|---|---:|:--:|:--:|---:|---:|---:|
| **with** peek (shipped, 231) | 231 | true | true | **2.7787** | 1.0 | 0.0 |
| **without** peek (PIT, 303) | 303 | true | true | **2.8268** | 1.0 | 0.0 |

**The claim survives.** Removing the peek does not weaken the conjugate reading — it *strengthens*
it slightly (2.78 → 2.83). So on this probe the look-ahead was **not inflating** the agreement.
That is consistent with the mechanism: the conjugate test asks whether ranks *transfer across
arms*, not what the return *level* is, and survivorship shifts levels rather than rank-transfer.

**Two things this does not license:**

1. **One probe is not a proof.** A single known-answer factor tested one way is evidence, not a
   theorem. A signal correlated with *survival itself* (a quality/low-vol-shaped factor) could
   behave differently, and that was not tested.
2. **`pbo = 0.0` exactly, in both universes.** An exact zero on a real CSCV bucket-transfer is the
   kind of number that usually means *saturated*, not *measured*. It is invariant to the peek, so
   it is not a look-ahead artifact — but it remains flagged (as it was in RR-Y1-028-V) as a
   separate instrument question that nobody should lean on yet.

---

## Q3 — PORTABILITY: BIST-local quirk, or a defect that travels?

**ADR-0002** (US micro-cap expansion) decides: *"Phases run data-feasibility → **infrastructure
port** → universe and data-quality probes → pre-registered measurement,"* with the stated
consequence *"reuse of the **market-agnostic engine** in a second market."*

The defect lives in `src/engine/moda.py::_eligible_names` — **inside the market-agnostic engine**,
not in any BIST-specific screening module. It takes a `Panel` and knows nothing about BIST.

### **PORTABLE DEFECT.** It ports by construction: the engine is what gets ported.

**And it is worse in the target market.** US micro-cap is precisely the population where a
window-median liquidity filter plus an attendance filter is most dangerous: delisting rates are
high, and liquidity is born and dies inside the window. A `[d0, d1]`-selected universe there keeps
the survivors and the late-liquid — the textbook survivorship trap, sitting directly on top of the
US track's own thesis (*institutional exclusion below liquidity thresholds*). Here it removed 39
dead + 59 dried-up names out of 303; in US micro-caps that fraction would be larger, not smaller.

**One component does *not* port:** the TÜFE indexing (D1b). With US CPI at ~2–3%/yr the deflator is
≈ 1.0 and that fix is a near-no-op. So **the US port would inherit the look-ahead *without* the
inflation problem that motivated the eligibility rewrite in the first place** — i.e. it would
inherit the bug and not the reason.

**Sequencing.** ADR-0002 already places *"universe and data-quality probes"* **before**
pre-registered measurement. That is the right slot to fix this — but only if the need is known
**before** the port, not discovered after it.

---

## Recommendation (a proposal, not a change)

**Priority: MEDIUM for BIST, HIGH as a pre-condition of the Yol-3 port.**

- **Not urgent for BIST verdicts.** No recorded verdict used it (Q2a = zero), and on the probe
  tested the conjugate answer does not move (Q2c). Nothing currently in flight is contaminated.
- **But it is a landmine for the port** (Q3), and it now sits in a live verdict path (Q2a "BUT").

**Decision-relevant fact for whoever writes the fix spec:** the PIT universe is **larger**
(303 > 231), comfortably above the 100 needed for two arms. **A point-in-time fix therefore does
not re-break Mod-A** — it does not reopen the D1 calibration problem RR-Y1-028 just solved. That
removes the main reason one might have hesitated.

**Shape of a candidate fix** (to be specified, frozen and direction-verified in a **separate**
ex-ante spec — the D1b lesson: an unmeasured direction nearly shipped inverted):

1. Liquidity from a **trailing** window ending at the split date, not a window median spanning the
   future.
2. Coverage from the **past** window, or dropped in favour of a per-date validity mask (the returns
   path already tolerates NaNs, so a name that dies mid-window can simply stop contributing rather
   than be excluded retroactively).
3. Ideally **expanding/rolling** eligibility recomputed per split date, so a long evaluation window
   does not get a single frozen universe at all.

**What the spec must measure before shipping** (each one a direction check, mirroring D1b):
the eligible count under the new rule; the survivor/casualty split it produces; and whether the
conjugate answer moves — on **more than one probe**, including at least one signal plausibly
correlated with survival.

**Out of scope here and deliberately not done:** any code change, any verdict change, and any
Mod-B/C repair.
