"""RR-Y3-001 (part 4) -- two loose ends, closed by measurement.

  1. Is GAIA really a LIVE micro-cap? If it is, then FMP's 402 on it proves the free tier is a
     SYMBOL WHITELIST (it cannot serve small companies at all) rather than a survivorship problem.
     If GAIA turned out to be delisted or huge, the conclusion would be different. Read its market
     cap from the one endpoint that answered 200 for every symbol: /profile.

  2. How deep does the FREE delisted-companies list go? A 100-row page-0 that cannot be paged is a
     teaser, not a dataset. Paged until it stops.

Output: demo x/out/y3_fmp_depth.json
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
OUT = Path(__file__).resolve().parents[2] / "docs" / "yol3" / "raw"
BASE = "https://financialmodelingprep.com/stable"


def key() -> str | None:
    k = os.environ.get("FMP_API_KEY")
    if k:
        return k
    env = Path(__file__).resolve().parents[2] / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.startswith("FMP_API_KEY="):
                return line.split("=", 1)[1].strip()
    return None


def main() -> None:
    k = key()
    doc: dict = {"id": "RR-Y3-001 part 4 -- FMP free-tier depth + the GAIA control"}

    # 1. the GAIA control
    prof = {}
    for sym in ("AAPL", "GAIA", "INFIQ"):
        r = requests.get(f"{BASE}/profile", params={"symbol": sym, "apikey": k}, timeout=30)
        j = r.json() if r.status_code == 200 else []
        p = j[0] if isinstance(j, list) and j else {}
        prof[sym] = {
            "companyName": p.get("companyName"),
            "marketCap": p.get("marketCap"),
            "exchange": p.get("exchange"),
            "isActivelyTrading": p.get("isActivelyTrading"),
            "price": p.get("price"),
        }
        time.sleep(0.4)
    doc["profile_control"] = {
        "rows": prof,
        "reading": (
            "if GAIA is an ACTIVELY TRADING company with a small market cap, then FMP's 402 on its "
            "quote/history/fundamentals is not about delisting at all -- the free tier simply does "
            "not carry small companies. That makes it useless for micro-cap research before "
            "survivorship even enters the picture."
        ),
    }
    for s, v in prof.items():
        mc = v.get("marketCap")
        print(f"  {s:<6} {str(v.get('companyName'))[:28]:<30} mcap={mc}  "
              f"active={v.get('isActivelyTrading')}  px={v.get('price')}", flush=True)

    # 2. how deep is the free delisted list?
    pages, rows, oldest = 0, 0, None
    seen_syms = []
    for p in range(25):
        r = requests.get(f"{BASE}/delisted-companies",
                         params={"page": p, "apikey": k}, timeout=30)
        if r.status_code != 200:
            doc.setdefault("delisted_pagination", {})["stopped_at_page"] = p
            doc["delisted_pagination"]["stop_http"] = r.status_code
            doc["delisted_pagination"]["stop_body"] = r.text[:160]
            break
        j = r.json()
        if not isinstance(j, list) or not j:
            doc.setdefault("delisted_pagination", {})["stopped_at_page"] = p
            doc["delisted_pagination"]["stop_reason"] = "empty page"
            break
        pages += 1
        rows += len(j)
        seen_syms += [x.get("symbol") for x in j]
        oldest = j[-1].get("delistedDate")
        time.sleep(0.35)

    ours = {"ALFI", "INFI", "MIMO", "SFT", "SI", "ARDS", "RBT", "DNMR", "WINS", "VINC",
            "ALFIQ", "INFIQ", "MIMOQ", "SFTGQ", "SICP", "RBTC", "WINSF"}
    doc.setdefault("delisted_pagination", {}).update({
        "pages_returned": pages,
        "rows_total": rows,
        "oldest_delistedDate_seen": oldest,
        "our_edgar_casualties_found": sorted(ours & set(seen_syms)),
        "n_ours_found": len(ours & set(seen_syms)),
    })
    print(f"\n  delisted list: {pages} pages, {rows} rows, oldest delistedDate seen = {oldest}")
    print(f"  our EDGAR casualties present: {sorted(ours & set(seen_syms))}")

    (OUT / "y3_fmp_depth.json").write_text(
        json.dumps(doc, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )
    print(f"\nwrote {OUT / 'y3_fmp_depth.json'}")


if __name__ == "__main__":
    main()
