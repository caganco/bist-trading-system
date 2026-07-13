"""RR-Y3-001 recon: build an INDEPENDENT delisted micro-cap sample from SEC EDGAR.

The sample must not come from the vendor being tested -- otherwise the test is circular ("does
EODHD know about the companies EODHD told me about?"). Form 25-NSE is the exchange's own
notification that it has removed a security from listing. It is the authoritative, free record of
a delisting event.

Zero cost. EDGAR requires only a descriptive User-Agent (SEC fair-access policy).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import requests

OUT = Path(__file__).resolve().parents[2] / "docs" / "yol3" / "raw"
OUT.mkdir(exist_ok=True)

UA = {"User-Agent": "sentio-research cagancebeci78@gmail.com"}
FTS = "https://efts.sec.gov/LATEST/search-index"


def fts(forms: str, start: str, end: str, size: int = 100) -> dict:
    params = {
        "q": '""',
        "forms": forms,
        "dateRange": "custom",
        "startdt": start,
        "enddt": end,
        "from": 0,
    }
    r = requests.get(FTS, params=params, headers=UA, timeout=30)
    print(f"  GET {r.url[:110]}... -> {r.status_code}", flush=True)
    r.raise_for_status()
    return r.json()


def main() -> None:
    print("[1] EDGAR full-text search, form 25-NSE (exchange delisting notice)", flush=True)
    try:
        d = fts("25-NSE", "2021-01-01", "2024-12-31")
    except Exception as exc:  # noqa: BLE001
        print(f"  FAILED: {type(exc).__name__}: {exc}")
        sys.exit(1)

    hits = d.get("hits", {})
    total = hits.get("total", {}).get("value")
    print(f"  total hits: {total}")
    rows = []
    for h in hits.get("hits", [])[:40]:
        s = h.get("_source", {})
        rows.append({
            "display_names": s.get("display_names"),
            "cik": s.get("ciks"),
            "file_date": s.get("file_date"),
            "form": s.get("file_type"),
            "adsh": s.get("adsh"),
        })
    print(f"  sample rows: {len(rows)}")
    for r in rows[:8]:
        print("   ", r["file_date"], r["display_names"])

    (OUT / "y3_edgar_25nse_raw.json").write_text(
        json.dumps({"total": total, "rows": rows}, indent=2), encoding="utf-8"
    )
    print(f"\nwrote {OUT / 'y3_edgar_25nse_raw.json'}")


if __name__ == "__main__":
    main()
