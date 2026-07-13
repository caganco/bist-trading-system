"""RR-Y3-001 (part 2) -- corrected EDGAR PIT/restatement detection + FMP's new API.

TWO CORRECTIONS TO MY OWN FIRST PASS, recorded rather than quietly overwritten:

  1. EDGAR restatement detection returned ZERO across five companies, which I did not trust.
     The bug was mine: in `companyfacts`, `fy`/`fp` are the fiscal year/period OF THE FILING that
     reported the fact, NOT of the fact's own period. A 2022 quarter re-reported inside the 2023
     10-K carries fy=2023 -- so grouping by (fy, fp) SEPARATES the two reports of the same period
     and can never see a restatement. The correct key is the ECONOMIC PERIOD: (tag, start, end).
     Regrouped here.

  2. FMP's v3 endpoints all returned HTTP 403 with "Legacy Endpoint ... only available for legacy
     users with valid subscriptions prior August 31, 2025". So the key in .env no longer reaches
     v3. FMP moved to a `/stable/` API; whether the free tier reaches THAT is a separate question
     and is measured here rather than assumed either way.

Output: demo x/out/y3_pit_and_fmp_v2.json
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


def sec_ua() -> dict[str, str]:
    """SEC fair-access policy requires a contact address in the User-Agent.

    Read from the environment, never committed. Unset -> fail loudly: a request without a
    contact is throttled or blocked by SEC, and a silently-degraded header would turn that
    into an unexplained empty result.
    """
    contact = os.environ.get("SEC_CONTACT_EMAIL", "").strip()
    if not contact:
        raise SystemExit(
            "SEC_CONTACT_EMAIL is not set. SEC EDGAR requires a contact address in the "
            "User-Agent (fair-access policy). Set it in .env -- see .env.example."
        )
    return {"User-Agent": f"sentio-research {contact}"}


UA = sec_ua()

# A wider net than the first pass: five delisted names PLUS three ordinary listed micro/small caps,
# because a restatement is a normal-company event and the failed names have sparse XBRL.
CIKS = {
    "INFINITY PHARMACEUTICALS (delisted)": 1113148,
    "Airspan Networks (delisted)": 1823882,
    "Aridis Pharmaceuticals (delisted)": 1614067,
    "Rubicon Technologies (delisted)": 1862068,
    "Danimer Scientific (delisted)": 1779020,
    "Silvergate Capital (delisted)": 1312109,
    "Vincerx Pharma (delisted)": 1786205,
}

TAGS = (
    "Revenues",
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "NetIncomeLoss",
    "Assets",
    "Liabilities",
    "StockholdersEquity",
    "CashAndCashEquivalentsAtCarryingValue",
    "OperatingIncomeLoss",
)


def scan_restatements(cik: int) -> dict:
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
    r = requests.get(url, headers=UA, timeout=45)
    if r.status_code != 200:
        return {"http": r.status_code}
    gaap = r.json().get("facts", {}).get("us-gaap", {})

    n_periods = 0
    n_conflict = 0
    examples = []
    for tag in TAGS:
        units = gaap.get(tag, {}).get("units", {}).get("USD", [])
        # THE FIX: group by the ECONOMIC PERIOD, not by the filing's fiscal year.
        by_period: dict[tuple, list] = defaultdict(list)
        for f in units:
            if f.get("form") not in ("10-Q", "10-K", "10-K/A", "10-Q/A"):
                continue
            by_period[(f.get("start"), f.get("end"))].append(f)

        for (start, end), facts in by_period.items():
            if len(facts) < 2:
                continue
            n_periods += 1
            vals = {f["val"] for f in facts}
            if len(vals) > 1:
                n_conflict += 1
                srt = sorted(facts, key=lambda x: (x["filed"], x["accn"]))
                first, last = srt[0], srt[-1]
                if len(examples) < 3:
                    examples.append({
                        "tag": tag,
                        "period": {"start": start, "end": end},
                        "n_distinct_values": len(vals),
                        "as_FIRST_reported": {
                            "filed": first["filed"], "form": first["form"],
                            "accn": first["accn"], "val": first["val"],
                        },
                        "as_LATER_reported": {
                            "filed": last["filed"], "form": last["form"],
                            "accn": last["accn"], "val": last["val"],
                        },
                        "delta": last["val"] - first["val"],
                        "delta_pct": (
                            round((last["val"] - first["val"]) / abs(first["val"]) * 100, 2)
                            if first["val"] else None
                        ),
                    })
    return {
        "http": 200,
        "n_periods_reported_more_than_once": n_periods,
        "n_periods_with_CONFLICTING_values": n_conflict,
        "restatement_rate": round(n_conflict / n_periods, 4) if n_periods else None,
        "examples": examples,
    }


def probe_fmp_stable() -> dict:
    key = os.environ.get("FMP_API_KEY")
    if not key:
        env = Path(__file__).resolve().parents[2] / ".env"
        if env.exists():
            for line in env.read_text(encoding="utf-8", errors="ignore").splitlines():
                if line.startswith("FMP_API_KEY="):
                    key = line.split("=", 1)[1].strip()
    if not key:
        return {"status": "CREDENTIAL-GATED"}

    out: dict = {"note": "key present in .env; never logged, never committed"}
    tests = {
        "stable/quote (AAPL, liveness)": ("https://financialmodelingprep.com/stable/quote", {"symbol": "AAPL"}),
        "stable/delisted-companies": ("https://financialmodelingprep.com/stable/delisted-companies", {"page": 0}),
        "stable/historical-price-eod/full (INFIQ, delisted)": (
            "https://financialmodelingprep.com/stable/historical-price-eod/full", {"symbol": "INFIQ"}),
        "stable/income-statement (INFIQ, delisted)": (
            "https://financialmodelingprep.com/stable/income-statement", {"symbol": "INFIQ", "limit": 5}),
    }
    for label, (url, params) in tests.items():
        try:
            r = requests.get(url, params={**params, "apikey": key}, timeout=30)
            body = r.text[:220]
            n = None
            try:
                j = r.json()
                n = len(j) if isinstance(j, list) else None
            except Exception:  # noqa: BLE001
                pass
            out[label] = {"http": r.status_code, "n_rows": n, "body_head": body}
        except Exception as exc:  # noqa: BLE001
            out[label] = {"error": f"{type(exc).__name__}: {exc}"[:180]}
        time.sleep(0.5)
    return out


def main() -> None:
    doc: dict = {
        "id": "RR-Y3-001 part 2 -- corrected EDGAR PIT detection + FMP new-API probe",
        "self_corrections": {
            "edgar_grouping": (
                "first pass grouped facts by (fy, fp) and found ZERO restatements. That key is "
                "wrong: in companyfacts, fy/fp describe the FILING, not the fact's period, so the "
                "original and the re-report of the same quarter land in DIFFERENT groups and can "
                "never be compared. Regrouped on the economic period (tag, start, end)."
            ),
            "fmp_v3": (
                "every v3 endpoint returned HTTP 403: 'Legacy Endpoint ... only available for "
                "legacy users with valid subscriptions prior August 31, 2025'. The key in .env "
                "does not reach v3. The /stable/ API is probed below rather than assumed."
            ),
        },
    }

    print("[EDGAR] restatement scan, regrouped on the ECONOMIC period ...", flush=True)
    ed = {}
    for name, cik in CIKS.items():
        try:
            ed[name] = scan_restatements(cik)
        except Exception as exc:  # noqa: BLE001
            ed[name] = {"error": f"{type(exc).__name__}"}
        r = ed[name]
        print(f"  {name:<38} periods>1: {r.get('n_periods_reported_more_than_once')}  "
              f"CONFLICTS: {r.get('n_periods_with_CONFLICTING_values')}", flush=True)
        time.sleep(0.3)
    doc["EDGAR_restatement_scan"] = ed
    total_conf = sum(v.get("n_periods_with_CONFLICTING_values") or 0 for v in ed.values())
    doc["EDGAR_total_conflicting_periods"] = total_conf

    print("\n[FMP] /stable/ API with the existing key ...", flush=True)
    doc["FMP_stable_api"] = probe_fmp_stable()
    for k, v in doc["FMP_stable_api"].items():
        if isinstance(v, dict):
            print(f"  {k:<48} http={v.get('http')}  n={v.get('n_rows')}", flush=True)

    (OUT / "y3_pit_and_fmp_v2.json").write_text(
        json.dumps(doc, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )
    print(f"\nwrote {OUT / 'y3_pit_and_fmp_v2.json'}")


if __name__ == "__main__":
    main()
