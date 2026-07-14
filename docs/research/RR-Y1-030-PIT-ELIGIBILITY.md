# RR-Y1-030 — Mod-A eligibility: point-in-time (look-ahead-safe) rewrite

**Class:** look-ahead-safety fix. **Not** an ADR-0005 math-bug exception — the old arithmetic was
correct; the **information set** was not. Strangler + additive discipline applies unchanged.

**Frozen spec:** `docs/yol1/STAGE0_RR-Y1-030_pit_eligibility.json` (committed **before** the new
rule was executed once). **Measurements:** `docs/yol1/RR-Y1-030_direction_probes_impact.json`.

---

## 0. The defect, and why the obvious fix would not have closed it

`moda._eligible_names` selected the Mod-A universe from **(a)** the *median over `[d0, d1]`* of each
name's trailing traded value and **(b)** *attendance over `[d0, d1]`*. Both read the **future** half
of the evaluation window relative to the split date. RR-Y1-029 measured the consequence: against a
point-in-time rule the window rule threw out **98** names — **39** delisted/halted out and **59**
that dried up — and admitted **26** that only became liquid later. Nothing unattributed. **It built
a universe of survivors.**

> **The trap.** Simply reverting the *statistic* to a trailing median would **not** have closed the
> look-ahead. RR-Y1-028's floor (`ELIGIBLE_ADV_FLOOR_TL = 2,000,000`) is denominated in
> **end-of-window TL**, so *comparing anything against it requires `TUFE(d1)`* — the future — before
> the window-median is even considered. The floor had to be re-anchored too.

**The invariant installed:**

> the eligible set at time *t* is a function of `{value_tl(s), tufe(s) : s ≤ t}` and frozen
> constants. **Nothing dated after *t* may change it.**

Enforced by a fuzz test that scribbles arbitrary data over the entire post-split half of the panel
(including killing every name) and asserts the eligible set is **byte-identical** — plus a mutation
that proves the test is not blind (the retained legacy rule *does* fail it).

---

## 1. The fix

| | before (RR-Y1-028) | after (RR-Y1-030) |
|---|---|---|
| liquidity | median over `[d0, d1]` of trailing-63d median | **trailing-63d median as of the split date** |
| floor | 2.0M TL in **end-of-window** TL (needs `TUFE(d1)`) | **227,611 TL in base-date TL**, CPI-indexed forward: `floor(t) = base × TUFE(t)/TUFE(base)` |
| attendance | ≥ 95% over `[d0, d1]` | **dropped** |

**The floor's real bar is unchanged — this is a change of reference point, not of the threshold.**
Evaluated forward, the base-anchored floor lands at **2,000,001 TL** at the end of the window
against the committed **2,000,000** anchor: **relative error 0.0**. A test pins the equivalence.

**Why attendance could simply be dropped.** There is no look-ahead-safe version of *"will this name
still be trading in the future"*, and a past-window coverage filter is degenerate here (the panel
starts 2019-01 and `d0` is 2019-07, so fewer than 252 business days precede it). It is also
**unnecessary**: the engine already tolerates a casualty — `_arm_active_series` and
`rank_ic_series` drop non-finite pairs per date and skip dates below the cross-section floor. A
name that dies simply **stops contributing from the day it stops trading**, instead of being
retroactively erased from the universe. That is what the returns/cost path has always done.

**Not done, and declared:** per-split-date *expanding* eligibility. Mod-A forms its arms **once**,
at `split_asof`, and holds them — that is the design of the conjugate test, not an accident.
Making that single decision information-safe fully closes the look-ahead; an expanding universe is
a different and larger question.

---

## 2. Direction verification — the D1b guard

In RR-Y1-028/D1b a CPI-indexing fix was **very nearly shipped with the sign inverted**, and the unit
test written beside it **encoded the inversion and passed**. The only thing that caught it was
deriving the expected magnitude independently. So the expectation here comes from **outside this
directive** — RR-Y1-029, a READ-ONLY diagnostic that ran before this fix existed — and the STOP
conditions were frozen in the spec.

```
legacy (window rule) : 231
PIT (this fix)       : 305       expected 303-310  (RR-Y1-029, independent)
STOP conditions fired: none
```

| STOP condition (frozen ex-ante) | fired? |
|---|:--:|
| universe **shrinks** (< 231) — the inverted direction | no |
| `n < 100` — Mod-A re-broken, undoing RR-Y1-028 | no |
| `n > 400` — the floor stopped biting once attendance was dropped | no |
| the future-injection test fails to catch a look-ahead-reintroducing mutation | no |

---

## 3. Multi-probe, including a **measured** survivorship-correlated signal

RR-Y1-029 tested **one** probe (hi52, momentum-shaped) and found the peek did not move the
conjugate answer. One probe is evidence, not a theorem — and the probe most likely to be moved by a
survivor-selected universe is one correlated with **survival itself**.

**The probe's validity is measured, not assumed** (a null from an uncorrelated probe proves
nothing). On this panel the casualties **are** the volatile names:

```
median 63d realized vol at d0 — casualties 0.0297   survivors 0.0233
=> lowvol63 IS survivorship-correlated.  Only then is its result interpretable.
```

| probe | with peek (231) | without peek (305) | Δt | verdict flipped? |
|---|---:|---:|---:|:--:|
| hi52 (RR-Y1-029's single probe) | 2.8170 | 2.5765 | −0.241 | **no** |
| mom120 | 0.2451 | −0.0078 | −0.253 | **no** |
| **lowvol63 — survivorship-correlated** | 5.1069 | **5.3923** | **+0.285** | **no** |
| value_static | 2.8216 | 2.9784 | +0.157 | **no** |

**No verdict flips on any probe** — including the one built to be maximally sensitive to the
survivorship channel. On that probe, removing the peek makes the reading **stronger** (+0.285): the
peek was mildly *suppressing* lowvol63, not inflating it. That is the **opposite** of the
survivorship-inflation worry, and it closes RR-Y1-029's limit-1.

> **But the peek is not inert, and that is the actual case for this fix.** It perturbs `t_cross` by
> roughly **±0.25** in both directions. No probe crossed the 2.0 bar here — but a candidate sitting
> at **t ≈ 2.1 with the peek would read 1.86 without it**. The look-ahead cannot manufacture an
> agreement out of nothing; it *can* decide a marginal one. That is enough to justify closing it,
> and it is why "no historical verdict changed" is not a reason to leave it open.

*(Scope guard: hi52 / mom120 / lowvol63 / value_static are **known-answer probes** used to measure
the instrument. All four are closed on the **independent** screening path (D-203/204/205/208,
NRR-007/008), which this directive does not touch. **No candidate is re-adjudicated.**)*

---

## 4. Impact — measured, not asserted (D3 discipline)

Every verdict-bearing field (`nw_t`, `gross/net_active_ann`, `cost_ann`, `dsr`,
`beats_benchmark_floor`) comes from the **eligibility-free** path: `harness._tilt_active` and
`modb` both use `panel.names` with a per-date mask. Changing eligibility must not move them **at
all** — and rather than assert that from first principles, it is **diffed against the values
recorded before the fix** in `docs/yol1/RR-Y1-028_d3_impact_scan.json`.

```
hi52    nw_t  4.34730877   (recorded before the fix: 4.347)
mom120  nw_t  1.42933690   (recorded before the fix: 1.429)
fields_that_moved: []
```

**BYTE-IDENTICAL.** No recorded verdict changes, confirming RR-Y1-029's scope finding by
measurement. (Expected: no committed verdict ever placed `agreement_pass` or the real CSCV `pbo` in
its keep-bar, and Mod-A could not execute on the real panel before RR-Y1-028 anyway.)

---

## 5. Strangler decision — and why it goes the other way here

**The old rule is fixed in place, not retained as the default.** Justification, measured rather than
assumed: RR-Y1-029 established that `_eligible_names` has **never contributed to a single recorded
verdict** — Mod-A never executed, Mod-C never ran, and no keep-bar contained agreement/PBO. There is
no committed result whose reproducibility depends on the old behaviour.

Keeping a look-ahead-**unsafe** universe builder as a co-equal default would be a **footgun**, not a
strangler: the next caller would face two functions and no way to tell which is safe.

**What *is* retained:** the window rule remains reachable via an explicit, loudly-named
`legacy_window_rule=True`, so RR-Y1-029's before/after comparison stays reproducible — and it does:
the RR-Y1-028-V attribution check still reproduces **38 / 43 / 72 / 231** exactly. A test pins that
the **default is the safe path**.

---

## 6. Portability (the reason this was worth doing now)

RR-Y1-029 established that this defect lives in the **market-agnostic engine**, which ADR-0002
explicitly ports to the Yol-3 US micro-cap track (*"infrastructure port"*, *"reuse of the
market-agnostic engine in a second market"*) — and that it is **worse** there, since US micro-cap is
the population where delisting and born-and-dying liquidity are most severe. The one component that
does **not** port is the CPI indexing (US CPI ≈ 2–3%/yr makes it a near-no-op), so the port would
have inherited **the bug without the reason for it**. It is now closed before the port, not after.

---

## 7. Out of scope (declared)

Mod-B (already clean — uses `panel.names`) · the `pbo = 0.0` diagnostic · the moda/modb/modc HAC
bandwidth at `h > 1` · per-split-date expanding eligibility (§1).
