# RR-Y1-028 — Validation-engine measurement-correctness fixes (D1d / D2 / D3 / D1a-b-c)

**Class:** instrument-correctness (tool repair). **Not** an edge hunt, **not** a re-measurement,
**not** a graveyard revival. No candidate is promoted, demoted or reopened by this work.

**ADR-0005 exception, declared explicitly:** three of these are genuine *mathematical bug fixes*
to committed engine paths. ADR-0005 permits exactly that and requires it to be marked rather than
made silently. This report, the commit messages and the code comments are that marking.

**Strangler discipline:** no committed field is deleted. `EngineOutput.real_active_ann` is
retained with its original meaning; the corrected quantity is added alongside as
`real_total_ann`. `_tilt_active`'s committed 3-tuple contract is untouched; the benchmark-carrying
variant is a new `_tilt_active_full`.

---

## 0. Why this exists

The engine emits the vector every Yol-1 verdict is read from. Four defects were found in it. Three
are arithmetic; one is an eligibility rule. Together they meant the engine **could not adjudicate a
candidate that had a real gross signal**:

| # | defect | effect |
|---|---|---|
| **D1d** | the Mod-A guard wrote `agreement_pass=False` when the leg **never ran** | *could not measure* was recorded as *measured and failed* |
| **D1a/b/c** | the Mod-A eligible universe admitted **38** names against the **100** needed | the conjugate leg has, in practice, **never executed** on real BIST data |
| **D2** | overlapping h-day returns annualized ×252 instead of ×252/h | gross/net/real inflated ~h-fold (at h=21: **21×**) |
| **D3** | the benchmark floor deflated an **active spread** and compared it to a **nominal** rate | a healthy tilt was auto-failed; the gate was effectively unpassable |

Two of the engine's five keep-bar conditions (`agreement_pass`, real CSCV `pbo`) had therefore
never once been produced from a real measurement, and a third (`beats_benchmark_floor`) was
dimensionally wrong.

---

## 1. D1d — an unmeasured gate is not a failed gate

**Was** (`moda.py::_agreement_guard`): a degenerate universe returned `agreement_pass = False`
and a NaN `pbo`. A consumer doing the natural thing — `bool(out.agreement_pass)`,
`out.pbo <= 0.50` — recorded **two FAILs for a leg that never executed**.

**Now:** `agreement_pass = None`, `agreement_measured = False`,
`AgreementConfidence.NOT_MEASURED`, and the guard's reason is carried verbatim instead of a
synthetic `arm=0 < 50` grade. `pbo_measured` distinguishes a real CSCV PBO from an absent one.

`src/engine/keep_bar.py` (new, additive) is the single place that reads the tri-state honestly:
a condition is `PASS` / `FAIL` / `NOT_MEASURED`, and a run with an unmeasured condition is
**INCONCLUSIVE**, never a DROP. A measured failure is still a DROP — the fix must not launder
real negatives, and a test pins that.

This is the code form of the project's own core discipline: *not detected ≠ does not exist*
(ADR-0007). **The engine's emitted numbers do not change** — only the honesty of their labels.

> Deliberate non-change: writing `None` into `out.pbo` would have newly activated the Mod-B proxy
> fallback in `harness.py` (today unreachable, because the guard writes NaN and `NaN is not None`).
> That is a separate finding and is out of scope here; `out.pbo` keeps its emitted value.

---

## 2. D2 — annualizing an overlapping horizon

`_returns_cost` builds its active series from `forward_return(panel, h)`: an **h-day** return
sampled on **every** trading day. Consecutive observations overlap by h−1 days. Its annualizer is
**252/h**, not 252.

The cost leg was *correct* (turnover really is daily, so 252 is right for it) — which is exactly
why `net = gross − cost` compared two different scales.

**Proof** (same signal, only `h` varies):

| h | engine's `gross_ann` (×252) | correct (×252/h) | inflation |
|---|---|---|---|
| 1 | −0.01626 | −0.01626 | **1.0×** |
| 5 | −0.03617 | −0.00723 | **5.0×** |
| 21 | −0.16269 | −0.00775 | **21.0×** |

Also fixed: the HAC bandwidth. `nw_lag` defaulted to 5 against a 21-day overlap, which understates
the standard error and inflates the t-stat. It now defaults to `max(NW_LAG_DAILY, h)`.
(`examples/rry1008` already passed `nw_lag=21` by hand — for precisely this reason. The engine
default did not.)

**Zero regression at h = 1** — `252/1 == 252`, byte-identical. Every engine unit test and the
committed PEAD Stage-0 run at h = 1, which is why this never surfaced. The one committed run at
h > 1 is VIOP-K2 (h = 21); its gross was a true zero, and 21 × 0 is still 0, so its verdict is
unaffected — **confirmed in the impact scan, not asserted**.

---

## 3. D3 — the benchmark floor deflated a difference

**Was** (`benchmark.py`): the harness handed it `net_active_ann` — the tilt **minus** its EW
benchmark, a *difference* — and it did two things that do not follow:

```
real_active = (1 + nominal_ACTIVE) / (1 + TUFE) - 1     # deflating a SPREAD
beats       = real_active > max(TUFE, TLREF)            # REAL vs NOMINAL
```

Deflation applies to levels, not differences: inflation is common to both legs of
`tilt − benchmark` and has already cancelled. Comparing the (wrongly) deflated spread against a
nominal rate then demanded a tilt beat **its own benchmark by more than inflation** — in a
~38%/yr-TUFE window, an unpassable bar for any honest long-only strategy.

**Now:** the gate judges the strategy's **TOTAL** nominal return (`EW-benchmark + net-active`)
against the nominal floor — like against like. `real_total_ann` and `benchmark_floor_real_ann` are
exposed so the real-vs-real comparison is available and gives the identical boolean.

### 3.1 Measurement-verification (mandatory for a headline-field fix)

`docs/yol1/RR-Y1-028_d3_measurement_verification.json` — **ALL_CHECKS_PASS: true**

**(a) Mechanical proof — root cause, from the committed record, as an arithmetic identity.**
No re-run, no reconstruction, no trust required. Solving the *committed* PEAD output for the
deflator that produced it:

```
recorded net_active_ann      = -0.07283490502363017
recorded real_active_ann     = -0.3301359003810652
=> implied deflator          =  0.384109
recorded benchmark_floor_ann =  0.3841092476874126
```

Identical to six decimals. The deflator's input **was** the active spread, and the result **was**
compared against the nominal floor. Established from the record itself, not from a claim.

**(b) Differential — same inputs, only D3 toggled.** The rc-vector (`gross`, `net`, `cost`, `tax`,
`mean_rt_bps`, `nw_t`, `n_obs`) is unchanged, and so are the floor's own inputs (TUFE, TLREF, the
nominal floor). The difference is confined to the gate: `False → True`. Real-vs-real agrees with
nominal-vs-nominal.

**(c) Sanity — the named case.** A tilt earning +5%/yr over an EW benchmark that itself returned
+60% nominal, in a ~35% inflation window: **old** → recorded as a −22.3% "real active", **FAIL**.
**New** → 65% total vs a 35% floor, **PASS**.

### 3.2 D3 impact scan — did the bug ever *decide* a verdict?

`docs/yol1/RR-Y1-028_d3_impact_scan.json`

`benchmark_floor` has exactly one caller (`harness`), so the blast radius is precisely the set of
production `harness()` invocations. **Enumerated from the code, not from memory** — the screening
records (d203…d213, nrr007/8) never touch the engine harness and were verified not to contain the
field.

The deciding question is **not** "does the gate flip". A flipped gate only contaminates a burial if
that field was in the record's keep-bar at all. Each row therefore carries an **evidence-cited**
`floor_in_keep_bar`, read from the committed record:

| candidate | gross | nw_t | old D3 | new D3 | floor in keep-bar? | class |
|---|---:|---:|:--:|:--:|:--:|---|
| PEAD (RR-Y1-014) | −0.0012 | −0.029 | False | True | **No** | FLOOR-NOT-IN-VERDICT |
| VIOP-K2 (SSF OI) | −0.0035 | −0.074 | False | False | **No** | FLOOR-NOT-IN-VERDICT |
| RR-Y1-008 :: hi52 | 0.1155 | 4.347 | False | True | **No** | FLOOR-NOT-IN-VERDICT |
| RR-Y1-008 :: mom120 | 0.0344 | 1.429 | False | True | **No** | FLOOR-NOT-IN-VERDICT |
| RR-Y1-008 :: value_static | 0.0180 | 0.658 | False | True | **No** | FLOOR-NOT-IN-VERDICT |

**D3-DETERMINED: 0.** No recorded verdict was contaminated, because every keep-bar in the blast
radius was decided on **NW-t**, which D3 does not touch:

- **PEAD** — frozen keep-bar: *full-panel NW-t ≥ 2.0 AND X2-lockbox NW-t ≥ 2.0* (−0.029 / −0.486).
  `beats_benchmark_floor` appears only in the diagnostics block.
- **VIOP-K2** — Stage-0 keep-bar is a single metric: `nw_t_rank_ic ≥ 2.0` (−0.073). The replay
  reproduces it (**−0.074**), which is also a fidelity check on this scan.
- **RR-Y1-008** — an *instrument exam*, not an edge verdict. The three factors' burials come from
  the screening path (D-203/204/205/208, NRR-007/008), which never calls `benchmark_floor`.

**No cold decision is required.** The damage from D3 was **prospective**: the gate would also have
failed a genuinely good candidate. That is what is now repaired.

> Recorded, not claimed: the scan's replay of `hi52` on the ALL-universe, **pre-cost** panel shows
> `gross = 0.1155, nw_t = 4.347`. This is a diagnostic of the scan, **not** a verdict and **not** a
> revival: hi52's closure rests on D-208's *fair-cost* screening measurement, an independent path
> this directive does not touch.

---

## 4. D1a/b/c — the Mod-A eligible universe (ex-ante frozen calibration)

**Pre-registration:** `docs/yol1/STAGE0_RR-Y1-028_D1_universe_calibration.json`, committed
**before** the recalibrated universe was ever built. **Result:**
`docs/yol1/RR-Y1-028_d1_calibration_result.json`.

### Root cause (diagnostics of the *old* rule; window 2019-07-03 → 2026-04-22, universe 681)

| filter | rule | admits |
|---|---|---:|
| **D1a/b** liquidity | trailing-63d ADV ≥ 10M TL, sampled at a **single** date (`d0`) | **48** |
| *(same floor at `d1`)* | *— pure currency erosion, not market structure* | *169* |
| **D1c** continuity | `min_cov = 1.0` — a non-NaN close on **every** one of ~1700 days | **74** |
| **both, as applied** | | **38** |
| **needed for two arms** | | **100** |

Each filter is independently below the bar, so fixing one would not have helped. And `min_cov=1.0`
is not a liquidity filter at all — it is a hidden survivorship/continuity filter that removes 89%
of the universe.

### The three frozen constants, each anchored ex-ante to reality — not to an outcome

- **`ELIGIBLE_ADV_FLOOR_TL = 2,000,000` (end-of-window TL, TUFE-indexed).** *Tradability* anchor,
  derived from the **committed cost model**: `D204_ORDER_VALUE_TL = 300,000/15 = 20,000 TL` per
  position; at a 2M TL median daily traded value that order is ~1% of a day's turnover — the region
  where the committed Kyle impact term is still negligible. 10M TL is not "wrong" as a *very
  liquid* marker; it is wrong as an *eligibility* floor, because it encodes a capacity constraint
  this operator does not have.

  **Mechanism, and its direction, stated explicitly** (this is easy to invert): the floor is
  **flat**, declared in end-of-window TL, and it is the **ADV series** that is deflated into that
  unit — each date's traded value is multiplied by `TUFE(end)/TUFE(t)`. That deflator is **> 1
  early** and **1.0 at the window's end**: 2019 turnover is scaled **up**, because 2019 TL bought
  more than 2026 TL. The early window therefore stops being penalised for the currency alone —
  precisely the distortion the old nominal floor introduced. Scaling the *floor* per-date would be
  algebraically equivalent, but the eligibility statistic is a window aggregate, which makes the
  direction of a floor-scaling easy to get backwards; deflating the series removes the ambiguity.
  A unit test pins the direction, and another pins that indexing does **not** admit a genuinely
  illiquid name.
- **`ELIGIBLE_MIN_COVERAGE = 0.95`.** *Listing-reality* anchor. A real BIST listing is not halt-free
  for seven straight years (VBTS measures, single-price auctions, suspensions). Demanding 100%
  attendance selects for the **absence of ordinary market events**, not for tradability.
  Deliberately **stricter** than this project's own precedent (K3/D-192: `MIN_TRADING_DAYS_PCT = 0.80`).
- **Window-median liquidity statistic.** The question is "was this name tradable over the window",
  not "on one particular morning" — least of all the panel's earliest and thinnest one.

**Why this is a calibration and not a threshold relaxation.** A relaxation lowers the bar on an
*existing* measurement. Here there **is** no measurement: the leg has never executed, so
`agreement_pass` and the real CSCV `pbo` have never been produced for **any** candidate. Making the
leg executable does not soften a verdict — it creates the possibility of one. **The condition of
that distinction is the ex-ante freeze**, which is why the constants were committed first. The
keep-bar itself (`AGREEMENT_CROSS_IC_T_MIN`, `SIGN_CONSISTENCY_MIN`, `PBO_THRESHOLD`, `DSR_MIN`)
and `MIN_NAMES_PER_ARM = 50` are **untouched** (DEC-049); `LIQUID_ADV_MIN_TL` is unchanged and still
governs `data_adapter.liquid_names`.

The pre-registration also fixes the failure condition in advance: *if the pool is still below 100,
the calibration has FAILED and is reported as such — the constants are not loosened until the leg
fires.*

### Result (post-freeze) — `docs/yol1/RR-Y1-028_d1_calibration_result.json`

| | old rule | calibrated |
|---|---:|---:|
| eligible names | **38** | **231** |
| needed for two arms | 100 | 100 |
| **Mod-A can run** | **no** | **yes** |

The TUFE deflator at the window's start is **8.79×** — 2019 turnover, expressed in end-of-window
TL, is scaled up by nearly nine. That single number is the size of the distortion the old nominal
floor carried. Eligible names' ADV profile (end-of-window TL): **min 2.0M · median 10.9M · max
808M** — the pool is not a collection of marginal listings.

**Mod-A executed on real BIST data for the first time.** Probe signal `hi52` (a known-answer
factor whose burial came from the *independent* D-208 fair-cost screening path):

```
agreement_measured = true      agreement_pass  = true
agreement_t_cross  = 2.8326    sign_consistency = 1.0
pbo (real CSCV)    = 0.0       confidence       = high
```

**This is an instrument check, not a verdict — and it must not be read as one.** The conjugate leg
answers one narrow question ("is there name-specific overfit?"). hi52's closure rests on something
the conjugate does not address at all: *net-of-fair-cost significance* (D-208, screening path).
RR-Y1-008 itself documented that a conjugate PASS can be a within-regime common-factor artifact —
which is precisely why `AgreementConfidence` exists. Nothing here reopens hi52, and this directive
does not touch the screening path.

What the run *does* establish is the thing it was frozen to test: `agreement_pass` and the real
CSCV PBO are now **measured quantities** instead of a guard message. Two of the engine's five
keep-bar conditions have gone from *never produced* to *produced*.

> Recorded, not smoothed over: `pbo = 0.0` exactly. For a strongly persistent style factor a
> perfect bucket-rank transfer is plausible, but an exact zero deserves scrutiny before anyone
> leans on it in a real adjudication.

### Scope

**Forward bar only.** No closed candidate is reopened because the instrument improved. Historical
candidates are the subject of the D3 impact scan, not of this calibration. ADR-0007 permanence
stands.

---

## 5. What this directive does NOT do

- It does **not** revive, re-run or re-adjudicate any graveyard or save/wait candidate.
- It does **not** change any recorded verdict — **and that is a measured finding** (impact scan:
  0 D3-DETERMINED), not an assumption.
- It does **not** touch the keep-bar constants.
- It does **not** claim an edge. The `hi52` numbers that appear in the impact scan and the
  calibration probe are **instrument diagnostics**, not verdicts.

## 6. Known residual (declared, out of scope)

`moda` / `modb` / `modc` still call `nw_lag_for(frequency)` without `h`, so their internal IC/HAC
bandwidth remains 5 even at h > 1. Correcting that would change *measured* conjugate and DSR
numbers and needs its own golden re-baseline — a separate directive. It is recorded here rather
than fixed quietly. (It has no effect on any committed verdict today, because Mod-A has never run
on real data — which is exactly what D1a/b/c changes going forward.)

## 7. Artifacts

| file | content |
|---|---|
| `src/engine/keep_bar.py` | **new** — tri-state keep-bar adjudication (NOT_MEASURED ≠ FAIL) |
| `src/engine/moda.py` | D1d guard + D1a/b/c eligibility |
| `src/engine/harness.py` | D2 annualizer + D3 total-return floor |
| `src/engine/benchmark.py` | D3 — the math fix |
| `src/engine/contracts.py` | new fields (additive), `nw_lag_for(frequency, h)` |
| `src/engine/config.py` | frozen D1 calibration constants |
| `docs/yol1/STAGE0_RR-Y1-028_D1_universe_calibration.json` | **frozen pre-registration** |
| `docs/yol1/RR-Y1-028_d1_calibration_result.json` | post-freeze calibration measurement |
| `docs/yol1/RR-Y1-028_d3_measurement_verification.json` | differential + mechanical proof + sanity |
| `docs/yol1/RR-Y1-028_d3_impact_scan.json` | full-set enumeration + classification |
| `tests/test_engine_keep_bar.py`, `test_engine_not_measured.py`, `test_engine_horizon_annualization.py`, `test_engine_eligibility.py` | **new** |
