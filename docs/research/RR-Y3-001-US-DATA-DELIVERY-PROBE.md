# RR-Y3-001 — US data-source **delivery probe** (Yol-3, Layer-0, zero cost)

**Class:** data-delivery test. **Not** an edge measurement, **not** a Stage-0, **not** a purchase.
**Zero-cost attestation:** no subscription, trial or purchase was made. Free tiers, public
endpoints, and one already-present free-tier key only.

**The rule this record enforces:** *"the vendor's docs say X" is not "X is in the series."* Every
axis below is **DELIVERED / MISSING / PARTIAL / NOT_MEASURED**, shown with data. An axis that
cannot be reached without paying or without a credential is **GATED** and is **not guessed at**.
**NOT_MEASURED ≠ delivers.**

Machine-readable: `docs/yol3/RR-Y3-001_delivery_probe_results.json`.

---

## 0. Headline — the free path is *not* where the received wisdom says it is

| assumption going in | what the measurement says |
|---|---|
| "Sharadar is needed for point-in-time fundamentals" | **Largely refuted.** SEC EDGAR delivers **as-reported PIT fundamentals with the full restatement history, for free.** It *is* the ground truth. |
| "restatements are an edge case" | **Refuted. Endemic in micro-cap.** Rubicon conflicts on **23 of 45** re-reported periods (51%); 6 of 7 companies show conflicts. |
| "free sources are enough to start" | **Refuted — but not for the expected reason.** yfinance's failure is **ticker reuse**, not just missing names. FMP's free tier does not carry **live** micro-caps at all. |
| "EODHD's free tier can answer this" | **Unknown.** No API key exists. Every EODHD axis is **NOT_MEASURED**. |

**The real gap is prices on delisted micro-caps — not fundamentals.** That reframes the paid
decision entirely, and it makes it much cheaper (§5).

---

## 1. The sample — built independently, and a trap caught in the building

A sample supplied by the vendor under test would make the probe circular. So it was built from the
**exchange's own delisting notices**: SEC **Form 25-NSE**.

```
8,050 Form 25-NSE filings 2021-2024
  1,300-filing slice  ->  356 distinct issuers
                      ->   87 still listed  (EXCLUDED)
                      ->   22 company-level delistings  (the sample)
```

> **The trap.** Form 25-NSE is filed **per security, not per company**. A naive pull returns
> **Goldman Sachs, Two Harbors and Gladstone** — they removed a *preferred series* or a *note*, not
> the company. Filtering on the form alone would have poisoned a "delisted micro-cap" sample with
> mega-caps that never left. The liveness filter (EDGAR's own `company_tickers.json`: a CIK absent
> from it no longer carries a listed ticker) removes them.

Ten confirmed failures were used for the survivorship test (Alfi, Infinity Pharma, Airspan, Shift,
**Silvergate**, Aridis, Rubicon, Danimer, Wins Finance, Vincerx). The sample also contains
take-privates and post-merger SPAC shells; those are **different events** and are kept separate —
survivorship bias is about the **casualties**.

---

## 2. AXIS: delisted price series — **yfinance MISSING, and the failure mode is worse than survivorship**

**4 of 10** EDGAR-confirmed casualties return **no data at all**. That much was expected. The part
that was not:

```
ALFI   ->  663 rows, 2015-11-10 .. 2018      <-- a DIFFERENT COMPANY that used to hold the ticker
ALFIQ  -> 1302 rows                          (the post-bankruptcy OTC symbol)
INFI   ->    0 rows                          (Infinity's actual listed ticker: EMPTY)
MIMO   ->    0     SFT -> 0     WINS -> 0     RBTC -> 0     DNMR -> 0
```

### **TICKER REUSE.** 

Querying the **pre-bankruptcy** ticker returns either **nothing** or **the wrong company's prices**.
A historical universe file therefore **cannot be joined to prices by ticker**: the join silently
yields either an empty series or a different company's history. This is a **silent** corruption —
it does not raise, it does not warn, and it *looks like data*.

*(This alone disqualifies ticker-keyed free price data for a survivorship-free US backtest. A
permanent identifier — CIK, or a vendor's own permaticker — is not a nicety, it is a requirement.)*

---

## 3. AXIS: FMP free tier — **MISSING, and not because of delisting**

The `402 Payment Required` on delisted names looked like a survivorship story. **It is not.** The
control that settles it:

| symbol | what it is | quote | history | fundamentals | profile |
|---|---|:--:|:--:|:--:|:--:|
| **AAPL** | mega-cap, live ($4.66T) | 200 | 200 | 200 | 200 |
| **GAIA** | **live micro-cap ($52.8M, actively trading, $2.11)** | **402** | **402** | **402** | 200 |
| INFIQ | delisted (Ch.11) | 402 | 402 | 402 | 200 |
| MIMO | delisted (Ch.11) | 402 | 402 | 402 | 200 |

**The free tier is a symbol whitelist, not an endpoint tier.** It refuses a *living, actively
trading* US micro-cap — exactly the target universe. Survivorship never enters the picture: the
**coverage is simply absent**.

Two further facts, recorded:
- Every legacy `/api/v3` endpoint now returns **403**: *"Legacy Endpoint … only available for legacy
  users with valid subscriptions prior August 31, 2025."* The key reaches `/stable/` only.
- The **`delisted-companies` list IS free** and carries `symbol / companyName / exchange / ipoDate /
  **delistedDate**`. But it returns **one page (100 rows)**, the oldest `delistedDate` seen is
  **2026-06-23**, and **none** of the 2021-2023 casualties appear. It is a *recent-delistings feed*,
  **not** a historical universe. **PARTIAL — a teaser, not a dataset.**

---

## 4. AXIS: PIT / restatement — **SEC EDGAR DELIVERS, and it is the ground truth**

XBRL `companyfacts` stamps **every fact** with the accession and the **filing date** that reported
it. So the same economic period reported **twice with different values** *is* a restatement —
**mechanically detectable, with no vendor at all.**

> **Self-correction, recorded rather than quietly overwritten.** My first scan found **zero**
> restatements across five companies, and I did not trust it. The bug was mine: in `companyfacts`,
> `fy`/`fp` describe the **filing**, not the fact's own period — so a 2022 quarter re-reported inside
> the 2023 10-K carries `fy=2023`, and grouping by `(fy, fp)` **separates the two reports of the same
> period and can never see a restatement**. Regrouped on the economic period `(tag, start, end)`:

| company (all delisted) | periods reported >1× | **conflicting** | rate |
|---|---:|---:|---:|
| Rubicon Technologies | 45 | **23** | **51%** |
| Infinity Pharmaceuticals | 272 | 22 | 8% |
| Danimer Scientific | 101 | 19 | 19% |
| Airspan Networks | 57 | 15 | 26% |
| Vincerx Pharma | 109 | 13 | 12% |
| Aridis Pharmaceuticals | 109 | 11 | 10% |
| Silvergate Capital | 46 | 0 | 0% |

### **Restatement is not an edge case in micro-cap. It is endemic.**

**Consequence:** any vendor that serves a **current view** instead of an **as-reported snapshot**
leaks future information into **every single backtest** on this universe. And because EDGAR gives
*both* values *and* their filing dates, **the answer key for testing any vendor's PIT claim is free.**

---

## 5. What EDGAR does **not** give — and why that reframes the paid decision

EDGAR carries **no prices**. Therefore:
- **no delisting return** (the CRSP convention treats it as a separate field; without it the
  backtest's return *on the delisting day* is simply missing — hidden survivorship even when the
  price series exists),
- **no market cap**, so no PIT micro-cap **universe construction**.

So the free path already covers **the hardest axis** (PIT as-reported fundamentals) and **the event
record** (Form 25-NSE). **The gap is a price source that carries delisted micro-caps with delisting
returns.** That is a *narrower and cheaper* problem than "buy Sharadar".

---

## 6. Decision matrix

| axis | SEC EDGAR (free) | yfinance (free) | FMP free tier | EODHD | Sharadar |
|---|---|---|---|---|---|
| delisting **event** record | ✅ **DELIVERED** | ✗ | 🟡 PARTIAL (teaser) | ⬛ NOT_MEASURED | ⬛ NOT_MEASURED |
| delisted **price series** | ✗ (no prices) | ❌ **MISSING** (+ ticker reuse) | ❌ **MISSING** (no micro-caps at all) | ⬛ NOT_MEASURED | ⬛ NOT_MEASURED |
| **delisting return** | ✗ by construction | ❌ | ❌ | ⬛ NOT_MEASURED | ⬛ NOT_MEASURED |
| **PIT as-reported** fundamentals | ✅ **DELIVERED — ground truth** | ✗ | ❌ | ⬛ NOT_MEASURED *(hypothesis below)* | ⬛ NOT_MEASURED |
| Form-4 insider (micro-cap) | ✅ free at source, **parse not built** | ✗ | ❌ | ⬛ NOT_MEASURED | ⬛ NOT_MEASURED |

**⬛ = GATED, not guessed.**

---

## 7. Gates — stated precisely, not vaguely

### EODHD — **CREDENTIAL-GATED. Every axis NOT_MEASURED.**

No `EODHD_API_KEY` in the environment (`.env` holds ANTHROPIC / EVDS / FINTABLES / FMP / TELEGRAM /
MKK). **To unblock:** register a **free** EODHD account (no payment) and set `EODHD_API_KEY` in
`.env`. The probe is written and runs unchanged; the 20-call/day free tier is enough for a
10-15 name sample.

**Schema evidence only** (public demo token, AAPL): the fields **`IsDelisted` and `UpdatedAt` exist**.
**Field existence is not delivery.** The demo token returns **403** on any delisted micro-cap, so it
cannot answer a single one of the four EODHD questions.

> **HYPOTHESIS — recorded, not counted as evidence.** `UpdatedAt` on AAPL fundamentals equals
> **today's date**, which is consistent with a **daily-refreshed current view** rather than an
> as-reported archive. If true, EODHD fundamentals carry **restatement leakage**.
>
> **The exact test, ready to run the moment a key exists:** take a period where EDGAR shows a
> conflict (§4 — e.g. Rubicon or Infinity), ask EODHD for that quarter, and compare. Returns the
> **later (restated)** value → current view → **unusable for a PIT backtest**. Returns the
> **first-reported** value → the PIT claim is **delivered**. EDGAR supplies both values *and* their
> filing dates, so the test is **decisive and free**.

### Sharadar — **PAID-GATED. NOT_MEASURED.**

Trial existence: **researched, UNVERIFIED.** The Nasdaq Data Link product page is JavaScript-rendered
and could not be read programmatically; public search did not confirm a free tier either. Recorded as
**unverified — not as "no trial exists."**

---

## 8. Payment trigger — written *before* anyone wants to spend money

**Sharadar (or any paid source) is bought only when ALL of the following hold:**

1. **The free path has actually been tried and failed.** That means: EODHD's **free** tier has been
   measured (it has not — no key), and the EDGAR-as-reported + a price source route has been shown
   *unable* to feed a PEAD Stage-0. Right now the free path has **not been exhausted; it has not
   been started.**
2. **A probe on the free-buildable subset shows a real edge signal.** Data quality is bought to
   *sharpen* a signal that already exists, never to *look for* one. (This is the whole lesson of the
   Yol-1 record: three candidates that looked real in-sample and died out-of-sample.)
3. **The specific gap is named.** Today the named gap is **delisted micro-cap prices + delisting
   returns** — not fundamentals. Any purchase must be justified against *that* gap, not against a
   general feeling that "better data would help".

**The cheapest next step is free:** register for EODHD and run the already-written probe — in
particular the restatement test in §7, whose answer key EDGAR already provides.

---

## 9. Web-claim overestimation ledger (a permanent lesson)

| claim found in the web/feasibility phase | verdict after measurement |
|---|---|
| "EODHD carries delisting flags" | **Schema only.** The field exists. Whether it is *populated for micro-caps* is **UNVERIFIED**. Field existence was read as delivery — that is the exact error this probe exists to prevent. |
| "Sharadar is required for point-in-time fundamentals" | **Largely refuted.** EDGAR delivers as-reported PIT with the full restatement chain, free. |
| "restatements are rare" (implicit) | **Refuted. Endemic** (up to 51% of re-reported periods in one micro-cap). |
| "free sources are a viable starting point" | **Refuted**, but the reason matters: yfinance fails via **ticker reuse** (silently wrong data, not just missing data), and FMP's free tier does not carry **live** micro-caps at all. |
| "minor companies, 10 years of fundamentals" (EODHD) | **NOT_MEASURED.** No key. |

---

## 10. Out of scope (declared)

Any payment or subscription · any Stage-0 edge measurement (this is a **data** test) · F1
infrastructure port (calendar / corporate actions) · broker & tax (F4) · the Form-4 parser
(free at source; the cost is effort, not money — flagged as a cheap follow-up, **not** claimed as done).
