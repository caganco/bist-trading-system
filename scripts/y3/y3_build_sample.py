"""RR-Y3-001 -- build an INDEPENDENT delisted US sample from SEC EDGAR (zero cost).

Independence matters: if the sample came from the vendor under test, the test would be circular
("does EODHD know about the companies EODHD told me about?"). Form 25-NSE is the EXCHANGE's own
notification that it removed a security from listing -- the authoritative, free record.

Two traps handled here, both discovered by looking at the raw data rather than assuming:

  1. Form 25-NSE is filed PER SECURITY, not per company. Goldman Sachs, Two Harbors and Gladstone
     all appear in the raw feed -- they were delisting a preferred series or a note, not the
     company. Filtering on the form alone would poison the sample with mega-caps that never left.

  2. "Still listed?" is answered by EDGAR's own current ticker file (company_tickers.json). A CIK
     absent from it no longer has a listed ticker. That is a free, vendor-independent liveness
     check.

Output: docs/yol3/raw/y3_delisted_sample.json
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

import requests

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
FTS = "https://efts.sec.gov/LATEST/search-index"
TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"

# preferred / notes / warrants / units -- NOT a company delisting
_NON_COMMON = re.compile(r"-P[A-Z]$|^.*[A-Z]{4}(L|N|Z|W|U|R)$|WS$|\.U$|\.W$")


def current_tickers() -> tuple[set[int], dict[int, str]]:
    r = requests.get(TICKERS_URL, headers=UA, timeout=30)
    r.raise_for_status()
    d = r.json()
    ciks, tick = set(), {}
    for v in d.values():
        ciks.add(int(v["cik_str"]))
        tick[int(v["cik_str"])] = v["ticker"]
    return ciks, tick


def fetch_25nse(start: str, end: str, pages: int = 4) -> list[dict]:
    rows = []
    for p in range(pages):
        params = {
            "q": '""', "forms": "25-NSE", "dateRange": "custom",
            "startdt": start, "enddt": end, "from": p * 10,
        }
        r = requests.get(FTS, params=params, headers=UA, timeout=30)
        if r.status_code != 200:
            break
        for h in r.json().get("hits", {}).get("hits", []):
            rows.append(h.get("_source", {}))
        time.sleep(0.2)  # SEC fair-access
    return rows


def parse(src: dict) -> dict | None:
    names = src.get("display_names") or []
    # the FIRST name is the issuer; the second is the exchange
    if not names:
        return None
    issuer = names[0]
    m = re.match(r"^(.*?)\s*(?:\(([^)]*)\))?\s*\(CIK (\d+)\)", issuer)
    if not m:
        return None
    name, tickers_blob, cik = m.group(1).strip(), (m.group(2) or ""), int(m.group(3))
    tickers = [t.strip() for t in tickers_blob.split(",") if t.strip()]
    common = [t for t in tickers if not _NON_COMMON.search(t)]
    return {
        "name": name,
        "cik": cik,
        "tickers_in_filing": tickers,
        "common_candidates": common,
        "file_date": src.get("file_date"),
        "exchange": names[1] if len(names) > 1 else None,
    }


def main() -> None:
    print("[1] EDGAR current ticker file (free liveness check) ...", flush=True)
    live_ciks, live_tick = current_tickers()
    print(f"    {len(live_ciks):,} CIKs currently have a listed ticker", flush=True)

    print("[2] Form 25-NSE, 2021-2023 (delisting notices) ...", flush=True)
    raw = []
    for yr in (2021, 2022, 2023):
        raw += fetch_25nse(f"{yr}-01-01", f"{yr}-12-31", pages=6)
    print(f"    {len(raw)} raw filings pulled", flush=True)

    seen, cands = set(), []
    for src in raw:
        p = parse(src)
        if not p or p["cik"] in seen:
            continue
        seen.add(p["cik"])
        p["still_listed_per_EDGAR"] = p["cik"] in live_ciks
        p["current_ticker_if_any"] = live_tick.get(p["cik"])
        cands.append(p)

    # a genuine company delisting: a common-stock ticker in the notice AND the CIK no longer
    # carries any listed ticker in EDGAR's own file.
    gone = [c for c in cands if c["common_candidates"] and not c["still_listed_per_EDGAR"]]
    still = [c for c in cands if c["still_listed_per_EDGAR"]]

    print(f"\n[3] parsed {len(cands)} distinct issuers")
    print(f"    still listed per EDGAR (preferred/notes delisting, or relisted): {len(still)}")
    print(f"    NO LONGER LISTED (company-level delisting candidates):          {len(gone)}")
    print("\n    sample of the excluded ones (the trap this filter catches):")
    for c in still[:4]:
        print(f"      {c['name'][:42]:<44} still listed as {c['current_ticker_if_any']}")
    print("\n    the delisted sample:")
    for c in gone[:20]:
        print(f"      {c['file_date']}  {str(c['common_candidates']):<14} {c['name'][:48]}")

    doc = {
        "id": "RR-Y3-001 -- independent delisted-company sample, built from SEC EDGAR (zero cost)",
        "source": "EDGAR full-text search, form 25-NSE (exchange notification of removal from listing)",
        "liveness_check": "EDGAR company_tickers.json -- a CIK absent from it no longer carries a listed ticker",
        "why_independent": "the sample must not come from the vendor under test, or the delivery test is circular",
        "trap_handled": (
            "Form 25-NSE is filed PER SECURITY. Goldman Sachs / Two Harbors / Gladstone appear in "
            "the raw feed because they removed a preferred series or a note -- not the company. "
            "Filtering on the form alone would have poisoned the sample with mega-caps."
        ),
        "n_raw_filings": len(raw),
        "n_distinct_issuers": len(cands),
        "n_still_listed_excluded": len(still),
        "n_delisted": len(gone),
        "delisted_sample": gone,
        "excluded_still_listed": still[:20],
    }
    (OUT / "y3_delisted_sample.json").write_text(
        json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\nwrote {OUT / 'y3_delisted_sample.json'}")


if __name__ == "__main__":
    main()
