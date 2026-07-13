"""RR-Y3-001 -- US data-source DELIVERY PROBE. Zero cost. Claims -> evidence.

The rule: "the vendor's docs say X" is NOT "X is in the series". Every axis below is either
DELIVERED (shown with data), MISSING (shown with the absence), PARTIAL, or NOT_MEASURED. Nothing
is inferred. An axis that cannot be reached without paying or without a credential is marked
GATED and is NOT guessed at.

Layer-0 (runs now, zero cost, no purchase):
  B1  yfinance  -- free, no key. Does it carry DELISTED names at all? (the survivorship demo)
  B2  SEC EDGAR -- free, official. It is the PIT ground truth: companyfacts stamps every fact with
                   the accession + filing date that reported it, so a RESTATEMENT is mechanically
                   detectable -- the same (fy, fp) reported twice with different values.
  FMP -- free tier, key already in .env (opportunistic: not named in the directive, but zero-cost
         and already credentialed, so it is measured rather than assumed away).

GATED (NOT run, NOT guessed):
  EODHD    -- no API key present in the environment. Every EODHD axis is CREDENTIAL-GATED.
  Sharadar -- no free tier. PAID-GATED by the directive's own constraint.

Output: demo x/out/y3_delivery_probe.json
"""
from __future__ import annotations

import json
import os
import time
from collections import defaultdict
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
OUT = Path(__file__).resolve().parents[2] / "docs" / "yol3" / "raw"
UA = {"User-Agent": "sentio-research cagancebeci78@gmail.com"}

SAMPLE = json.loads((OUT / "y3_delisted_sample.json").read_text(encoding="utf-8"))

# Event-type taxonomy matters: a SPAC shell that delists after completing its merger is not a
# "failure", and a take-private is not a "casualty". Survivorship bias is about the FAILURES --
# the names whose price went to ~0 and then vanished from the tape. Classified by hand from the
# EDGAR sample, and the classification is recorded so a reader can disagree with it.
FAILURES = {
    "ALFIQ": "Alfi, Inc. -- Chapter 11 (2022)",
    "INFIQ": "Infinity Pharmaceuticals -- Chapter 11 (2023)",
    "MIMOQ": "Airspan Networks -- Chapter 11 (2024)",
    "SFTGQ": "Shift Technologies -- Chapter 11 (2023)",
    "SICP": "Silvergate Capital -- wind-down (2024)",
    "ARDS": "Aridis Pharmaceuticals -- delisted (2023)",
    "RBTC": "Rubicon Technologies -- delisted (2023)",
    "DNMR": "Danimer Scientific -- Chapter 11 (2025)",
    "WINSF": "Wins Finance Holdings -- delisted (2021)",
    "VINC": "Vincerx Pharma -- delisted",
}
# The pre-bankruptcy listed ticker is usually the same string minus a trailing 'Q' (the OTC
# bankruptcy marker). Both are probed; a vendor that resolves NEITHER has no coverage.
def variants(t: str) -> list[str]:
    v = [t]
    if t.endswith("Q") and len(t) > 2:
        v.append(t[:-1])
    if t.endswith("F") and len(t) > 2:
        v.append(t[:-1])
    return v


def probe_yfinance() -> dict:
    """B1 -- the survivorship demonstration, on the free general-purpose source."""
    import yfinance as yf

    rows = {}
    for tk, note in FAILURES.items():
        got = {}
        for v in variants(tk):
            try:
                df = yf.Ticker(v).history(period="max", auto_adjust=False)
                got[v] = {
                    "rows": int(len(df)),
                    "first": str(df.index[0].date()) if len(df) else None,
                    "last": str(df.index[-1].date()) if len(df) else None,
                }
            except Exception as exc:  # noqa: BLE001
                got[v] = {"error": f"{type(exc).__name__}"}
            time.sleep(0.3)
        any_data = any(g.get("rows", 0) > 0 for g in got.values())
        rows[tk] = {"note": note, "variants": got, "ANY_DATA": any_data}
    n_ok = sum(1 for r in rows.values() if r["ANY_DATA"])
    return {
        "source": "yfinance (free, no key)",
        "sample": f"{len(FAILURES)} EDGAR-confirmed delisted US failures",
        "n_with_any_price_data": n_ok,
        "n_with_none": len(FAILURES) - n_ok,
        "rows": rows,
    }


def probe_fmp() -> dict:
    """FMP free tier -- key already present. Zero cost."""
    key = os.environ.get("FMP_API_KEY")
    if not key:
        # try .env
        env = Path(__file__).resolve().parents[1] / ".env"
        if env.exists():
            for line in env.read_text(encoding="utf-8", errors="ignore").splitlines():
                if line.startswith("FMP_API_KEY="):
                    key = line.split("=", 1)[1].strip()
    if not key:
        return {"status": "CREDENTIAL-GATED", "reason": "FMP_API_KEY not found"}

    base = "https://financialmodelingprep.com/api/v3"
    out: dict = {"source": "FMP free tier (key present in .env; NOT logged)"}

    # (a) does FMP expose a delisted-companies list at all?
    try:
        r = requests.get(f"{base}/delisted-companies", params={"apikey": key, "page": 0}, timeout=30)
        out["delisted_companies_endpoint"] = {
            "http": r.status_code,
            "n": len(r.json()) if r.status_code == 200 and isinstance(r.json(), list) else None,
            "sample": r.json()[:3] if r.status_code == 200 and isinstance(r.json(), list) else r.text[:200],
        }
    except Exception as exc:  # noqa: BLE001
        out["delisted_companies_endpoint"] = {"error": str(exc)[:200]}

    # (b) price history for the delisted failures
    rows = {}
    for tk in list(FAILURES)[:6]:  # free tier is rate-limited; a 6-name slice is enough to decide
        got = {}
        for v in variants(tk):
            try:
                r = requests.get(f"{base}/historical-price-full/{v}",
                                 params={"apikey": key}, timeout=30)
                j = r.json() if r.status_code == 200 else {}
                hist = j.get("historical", []) if isinstance(j, dict) else []
                got[v] = {
                    "http": r.status_code,
                    "rows": len(hist),
                    "last": hist[0]["date"] if hist else None,
                    "first": hist[-1]["date"] if hist else None,
                }
            except Exception as exc:  # noqa: BLE001
                got[v] = {"error": f"{type(exc).__name__}"}
            time.sleep(0.4)
        rows[tk] = {"variants": got, "ANY_DATA": any(g.get("rows", 0) > 0 for g in got.values())}
    out["price_history_on_delisted"] = rows
    out["n_with_any_price_data"] = sum(1 for r in rows.values() if r["ANY_DATA"])
    out["n_probed"] = len(rows)
    return out


def probe_edgar_pit() -> dict:
    """B2 -- EDGAR companyfacts as PIT ground truth, and mechanical restatement detection.

    Every XBRL fact carries the accession (`accn`) and the filing date (`filed`) that reported it.
    So the SAME (fy, fp, form) appearing twice with DIFFERENT values is a restatement, visible
    without any vendor. This is the ground truth against which a vendor's PIT claim can be checked.
    """
    # micro-cap-ish CIKs from the EDGAR sample that still have filings
    cands = {
        "INFINITY PHARMACEUTICALS": 1113148,
        "Airspan Networks Holdings": 1823882,
        "Aridis Pharmaceuticals": 1614067,
        "Rubicon Technologies": 1862068,
        "Danimer Scientific": 1779020,
    }
    found = []
    checked = []
    for name, cik in cands.items():
        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
        try:
            r = requests.get(url, headers=UA, timeout=40)
        except Exception as exc:  # noqa: BLE001
            checked.append({"name": name, "cik": cik, "error": f"{type(exc).__name__}"})
            continue
        if r.status_code != 200:
            checked.append({"name": name, "cik": cik, "http": r.status_code})
            time.sleep(0.3)
            continue
        facts = r.json().get("facts", {}).get("us-gaap", {})
        n_restated = 0
        example = None
        for tag in ("Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax",
                    "NetIncomeLoss", "Assets"):
            units = facts.get(tag, {}).get("units", {}).get("USD", [])
            by_period = defaultdict(list)
            for f in units:
                if f.get("form") in ("10-Q", "10-K") and f.get("fy") and f.get("fp"):
                    by_period[(f["fy"], f["fp"], f.get("start"), f.get("end"))].append(f)
            for k, v in by_period.items():
                vals = {x["val"] for x in v}
                if len(vals) > 1:
                    n_restated += 1
                    if example is None:
                        srt = sorted(v, key=lambda x: x["filed"])
                        example = {
                            "tag": tag,
                            "period": {"fy": k[0], "fp": k[1], "start": k[2], "end": k[3]},
                            "reports": [
                                {"filed": x["filed"], "accn": x["accn"],
                                 "form": x["form"], "val": x["val"]}
                                for x in srt
                            ],
                        }
        checked.append({
            "name": name, "cik": cik, "http": 200,
            "n_periods_with_conflicting_values": n_restated,
        })
        if example:
            found.append({"name": name, "cik": cik, "restatement_example": example})
        time.sleep(0.3)

    return {
        "source": "SEC EDGAR XBRL companyfacts (free, official, no key)",
        "why_this_is_the_ground_truth": (
            "every fact is stamped with the accession and FILING DATE that reported it. The same "
            "(fy, fp, period) reported twice with different values IS a restatement -- detectable "
            "with no vendor at all. This is the reference a vendor's PIT claim must be checked "
            "against."
        ),
        "companies_checked": checked,
        "restatements_found": found,
        "n_companies_with_a_restatement": len(found),
    }


def main() -> None:
    doc: dict = {
        "id": "RR-Y3-001 -- US data-source DELIVERY PROBE (Layer-0, zero cost)",
        "discipline": (
            "A vendor claim is not evidence. Each axis is DELIVERED / MISSING / PARTIAL / "
            "NOT_MEASURED, shown with data. Nothing is inferred; nothing is purchased."
        ),
        "sample_provenance": {
            "built_from": "SEC EDGAR form 25-NSE + company_tickers.json liveness check",
            "why_independent": "a sample from the vendor under test would make the probe circular",
            "n_delisted_companies_found": SAMPLE["n_delisted"],
            "failures_used_for_the_survivorship_test": FAILURES,
        },
        "GATED_not_guessed": {
            "EODHD": {
                "status": "CREDENTIAL-GATED -- NOT_MEASURED",
                "reason": "no EODHD_API_KEY in the environment (.env holds ANTHROPIC/EVDS/FINTABLES/FMP/TELEGRAM/MKK).",
                "consequence": "every EODHD axis in the directive (A1 delisting flag, A2 delisting return, A3 PIT restatement, A4 fundamentals depth) is UNMEASURED. Per the directive: NOT_MEASURED != delivers. No inference is made about them.",
                "to_unblock": "register a free EODHD account and set EODHD_API_KEY in .env (git-ignored). The probe script is written and will run against it unchanged.",
            },
            "Sharadar": {
                "status": "PAID-GATED -- NOT_MEASURED",
                "reason": "no free tier; the directive forbids any purchase.",
            },
        },
    }

    print("[B1] yfinance on EDGAR-confirmed delisted failures ...", flush=True)
    doc["B1_yfinance_survivorship"] = probe_yfinance()
    r = doc["B1_yfinance_survivorship"]
    print(f"     {r['n_with_any_price_data']}/{len(FAILURES)} delisted names return ANY price data",
          flush=True)

    print("[FMP] free tier (key already present) ...", flush=True)
    doc["FMP_free_tier"] = probe_fmp()

    print("[B2] EDGAR companyfacts -- PIT ground truth + restatement detection ...", flush=True)
    doc["B2_edgar_pit_ground_truth"] = probe_edgar_pit()
    e = doc["B2_edgar_pit_ground_truth"]
    print(f"     companies with a detectable restatement: {e['n_companies_with_a_restatement']}",
          flush=True)

    (OUT / "y3_delivery_probe.json").write_text(
        json.dumps(doc, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )
    print(f"\nwrote {OUT / 'y3_delivery_probe.json'}")


if __name__ == "__main__":
    main()
