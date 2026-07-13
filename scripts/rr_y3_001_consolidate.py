"""RR-Y3-001 -- consolidate the delivery-probe measurements into one committed record.

Reads the raw probe outputs (produced under a git-ignored scratch dir) and writes a single,
key-free, public-clean artifact. Asserts no credential leaked into the record.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRATCH = REPO / "demo x" / "out"
OUT = REPO / "docs" / "yol3" / "RR-Y3-001_delivery_probe_results.json"

SRC = {
    "sample": "y3_delisted_sample.json",
    "probe": "y3_delivery_probe.json",
    "pit_fmp": "y3_pit_and_fmp_v2.json",
    "fmp_scope": "y3_fmp_scope.json",
    "fmp_depth": "y3_fmp_depth.json",
}

_SECRET = re.compile(r"apikey|api_token|api_key|[A-Za-z0-9]{28,}", re.I)


def scrub(o):
    """Defence in depth: no query string, no long token-shaped string reaches the record."""
    if isinstance(o, dict):
        return {k: ("<redacted>" if _SECRET.search(str(k)) else scrub(v)) for k, v in o.items()}
    if isinstance(o, list):
        return [scrub(x) for x in o]
    if isinstance(o, str) and _SECRET.search(o):
        return _SECRET.sub("<redacted>", o)
    return o


def main() -> None:
    parts = {}
    for k, fn in SRC.items():
        p = SCRATCH / fn
        if not p.exists():
            print(f"MISSING: {p}")
            sys.exit(1)
        parts[k] = json.loads(p.read_text(encoding="utf-8"))

    sample = parts["sample"]
    probe = parts["probe"]
    pit = parts["pit_fmp"]
    scope = parts["fmp_scope"]
    depth = parts["fmp_depth"]

    yf = probe["B1_yfinance_survivorship"]
    edgar = pit["EDGAR_restatement_scan"]

    doc = {
        "id": "RR-Y3-001 -- US data-source DELIVERY PROBE (Layer-0, zero cost)",
        "class": "data-delivery test. NOT an edge measurement, NOT a Stage-0, NOT a purchase.",
        "discipline": (
            "A vendor's documentation is not evidence. Every axis is DELIVERED / MISSING / PARTIAL "
            "/ NOT_MEASURED, shown with data. An axis that cannot be reached without paying or "
            "without a credential is GATED and is NOT guessed at. NOT_MEASURED != delivers."
        ),
        "zero_cost_attestation": "No subscription, trial or purchase was made. Only free tiers, public endpoints and an already-present free-tier key were used.",
        "credential_hygiene": "The FMP key was read from .env (git-ignored), never logged, never written to any artifact. This record is scrubbed and asserted key-free.",

        "SAMPLE": {
            "why_independent": "a sample supplied by the vendor under test would make the probe circular",
            "built_from": "SEC EDGAR form 25-NSE (exchange notification of removal from listing) + company_tickers.json liveness check",
            "trap_caught": sample["trap_handled"],
            "n_raw_filings": sample["n_raw_filings"],
            "n_distinct_issuers": sample["n_distinct_issuers"],
            "n_excluded_still_listed": sample["n_still_listed_excluded"],
            "n_company_level_delistings": sample["n_delisted"],
            "failures_used": probe["sample_provenance"]["failures_used_for_the_survivorship_test"],
        },

        "AXIS_1_delisting_event_record": {
            "SEC_EDGAR": {
                "verdict": "DELIVERED (free, official)",
                "evidence": "form 25-NSE is the exchange's own delisting notice. 8,050 filings 2021-2024; a 1,300-filing slice yielded 356 distinct issuers, of which 22 are company-level delistings after removing per-security noise.",
                "caveat": "filed PER SECURITY -- a naive pull returns Goldman Sachs and Two Harbors (they delisted a preferred series, not the company). Requires the liveness filter used here.",
            },
            "FMP_free_tier": {
                "verdict": "PARTIAL -- a teaser, not a dataset",
                "evidence": depth["delisted_pagination"],
                "reading": "the delisted-companies list IS free and carries symbol / companyName / exchange / ipoDate / delistedDate. But it returns ONE page (100 rows), the oldest delistedDate seen is 2026-06-23, and NONE of the 2021-2023 EDGAR-confirmed casualties appear. It is a recent-delistings feed, not a historical universe.",
            },
            "EODHD": {"verdict": "NOT_MEASURED -- CREDENTIAL-GATED"},
        },

        "AXIS_2_delisted_price_series": {
            "yfinance": {
                "verdict": "MISSING -- and the failure mode is worse than survivorship",
                "n_casualties_probed": len(yf["rows"]),
                "n_with_any_price_data": yf["n_with_any_price_data"],
                "n_with_none": yf["n_with_none"],
                "THE_REAL_TRAP": (
                    "TICKER REUSE. Querying the PRE-bankruptcy ticker 'ALFI' returns 663 rows dated "
                    "2015-11-10 to 2018 -- a DIFFERENT company that previously held the symbol. "
                    "Meanwhile 'INFI' (Infinity's listed ticker) returns 0 rows, and MIMO / SFT / "
                    "WINS / RBTC / DNMR return nothing at all. So a historical universe file cannot "
                    "be joined to prices BY TICKER: the join silently returns either nothing, or "
                    "the wrong company."
                ),
                "rows": yf["rows"],
            },
            "FMP_free_tier": {
                "verdict": "MISSING -- and not because of delisting",
                "THE_CONTROL_THAT_SETTLES_IT": scope["profile_control"]["rows"]
                if "profile_control" in scope else depth["profile_control"]["rows"],
                "matrix": scope["endpoint_vs_symbol_matrix"],
                "reading": (
                    "the free tier is a SYMBOL WHITELIST, not an endpoint tier. GAIA -- a LIVE, "
                    "actively-trading US micro-cap with a ~$53M market cap, i.e. exactly the target "
                    "universe -- returns HTTP 402 on quote, price history AND fundamentals. AAPL "
                    "returns 200 on all three. So FMP's free tier cannot serve micro-caps at all, "
                    "living or dead. Survivorship never even enters the picture: the coverage is "
                    "simply absent."
                ),
                "note_on_v3": "every legacy /api/v3 endpoint now returns HTTP 403: 'Legacy Endpoint ... only available for legacy users with valid subscriptions prior August 31, 2025'. The key reaches /stable/ only.",
            },
            "EODHD": {"verdict": "NOT_MEASURED -- CREDENTIAL-GATED"},
        },

        "AXIS_3_delisting_RETURN": {
            "status": "NOT_MEASURED across every free source",
            "why_it_matters": (
                "the CRSP convention treats the delisting return as a SEPARATE field. Without it, a "
                "backtest's return on the delisting day is simply missing -- which is hidden "
                "survivorship even when the price series itself is present."
            ),
            "SEC_EDGAR": "does not carry prices at all -> cannot supply it, by construction.",
            "yfinance": "no such field. The series simply stops (or never existed).",
            "FMP_free_tier": "unreachable -- 402 on price history for any micro-cap.",
            "EODHD": "NOT_MEASURED -- CREDENTIAL-GATED.",
        },

        "AXIS_4_PIT_as_reported_fundamentals_and_RESTATEMENT": {
            "SEC_EDGAR": {
                "verdict": "DELIVERED -- and it IS the ground truth",
                "mechanism": (
                    "XBRL companyfacts stamps EVERY fact with the accession and the FILING DATE that "
                    "reported it. The same economic period reported twice with different values IS a "
                    "restatement -- mechanically detectable with no vendor at all."
                ),
                "self_correction_recorded": pit["self_corrections"]["edgar_grouping"],
                "MEASURED_RESULT": {
                    "companies_scanned": len(edgar),
                    "total_conflicting_periods": pit["EDGAR_total_conflicting_periods"],
                    "per_company": {
                        k: {
                            "periods_reported_more_than_once": v.get("n_periods_reported_more_than_once"),
                            "periods_with_CONFLICTING_values": v.get("n_periods_with_CONFLICTING_values"),
                            "restatement_rate": v.get("restatement_rate"),
                        }
                        for k, v in edgar.items()
                    },
                    "examples": {k: v.get("examples") for k, v in edgar.items() if v.get("examples")},
                },
                "THE_FINDING": (
                    "restatement is NOT an edge case in micro-cap -- it is ENDEMIC. Rubicon "
                    "Technologies conflicts on 23 of 45 re-reported periods (51%). Six of seven "
                    "companies show conflicts. So any vendor that serves a CURRENT VIEW instead of "
                    "an AS-REPORTED snapshot leaks future information into every single backtest on "
                    "this universe."
                ),
            },
            "EODHD": {
                "verdict": "NOT_MEASURED -- CREDENTIAL-GATED",
                "schema_evidence_only": {
                    "note": "the public demo token (AAPL only) confirms the FIELDS EXIST. Field existence is NOT delivery.",
                    "IsDelisted_field_exists": True,
                    "UpdatedAt_field_exists": True,
                    "UpdatedAt_value_for_AAPL": "2026-07-13 (today's date at probe time)",
                    "demo_token_on_a_delisted_microcap": "HTTP 403 Forbidden -- the demo token is restricted to a handful of symbols and cannot answer any micro-cap question.",
                },
                "HYPOTHESIS_to_test_when_a_key_exists": (
                    "UpdatedAt on AAPL fundamentals equals TODAY'S DATE, which is consistent with a "
                    "daily-refreshed CURRENT VIEW rather than an as-reported archive. If so, EODHD "
                    "fundamentals would carry restatement leakage. This is a HYPOTHESIS, not a "
                    "finding: it is recorded with its exact test (below) and is NOT counted as "
                    "evidence either way."
                ),
                "EXACT_TEST_ready_to_run": (
                    "pick a period where EDGAR shows a conflict (see the examples above -- e.g. "
                    "Rubicon or Infinity). Ask EODHD for that quarter. If EODHD returns the LATER "
                    "(restated) value, its fundamentals are a current view and are unusable for a "
                    "PIT backtest without an as-reported archive. If it returns the FIRST-reported "
                    "value, the PIT claim is delivered. EDGAR supplies both values and their filing "
                    "dates, so the test is decisive and free."
                ),
            },
            "Sharadar": {"verdict": "NOT_MEASURED -- PAID-GATED"},
        },

        "AXIS_5_Form4_insider_microcap": {
            "SEC_EDGAR": {
                "verdict": "DELIVERED IN PRINCIPLE (free, official) -- NOT YET PARSED",
                "reading": "Form 4 is filed with the SEC; EDGAR is the ORIGIN of every vendor's insider feed. Access is free. The cost is not money, it is parsing/normalisation effort.",
                "status": "the parse was NOT built in this probe (out of the F0 delivery-test scope). Marked as a KNOWN, cheap follow-up rather than claimed as done.",
            },
            "Sharadar_SF2": {"verdict": "NOT_MEASURED -- PAID-GATED"},
        },

        "GATES": {
            "EODHD": {
                "status": "CREDENTIAL-GATED -- every axis NOT_MEASURED",
                "reason": "no EODHD_API_KEY in the environment (.env holds ANTHROPIC / EVDS / FINTABLES / FMP / TELEGRAM / MKK).",
                "to_unblock": "register a FREE EODHD account (no payment) and set EODHD_API_KEY in .env. The probe is written and will run unchanged against it; the 20-call/day free tier is enough for the 10-15 name sample.",
            },
            "Sharadar": {
                "status": "PAID-GATED -- NOT_MEASURED",
                "trial_research": "attempted. The Nasdaq Data Link product page (data.nasdaq.com/databases/SFA) is JavaScript-rendered and could not be read programmatically; no free-trial tier was confirmed from the public search results either. Recorded as UNVERIFIED -- NOT as 'no trial exists'.",
                "what_would_be_measured_if_paid": [
                    "SEP: is there a separate delisting-RETURN field, or does the series merely stop?",
                    "SF1 ARQ dimension: as-reported vs restated -- checked against the EDGAR conflicts found above (EDGAR gives the answer key for free).",
                    "SF2: Form-4 transaction density on a micro-cap slice -- is it populated below $300M market cap?",
                ],
            },
        },
    }

    doc = scrub(doc)
    blob = json.dumps(doc, ensure_ascii=False)
    assert "apikey=" not in blob.lower(), "credential leaked into the record"
    assert "api_token=" not in blob.lower(), "credential leaked into the record"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT}  ({OUT.stat().st_size:,} bytes, key-free assertions passed)")


if __name__ == "__main__":
    main()
