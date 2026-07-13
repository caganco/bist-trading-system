"""RR-Y3-001 (part 3) -- what EXACTLY does the FMP free tier deliver?

The /stable/ probe returned 402 (Payment Required) for a DELISTED symbol on both price history and
fundamentals, while /stable/quote and /stable/delisted-companies returned 200. Two very different
worlds hide behind that:

  (a) the ENDPOINT is paid            -> free tier is useless for any backtest, listed or not
  (b) the SYMBOL is paid (delisted)   -> free tier works on live names but hides the casualties,
                                         which is the survivorship trap in its purest form

Those have opposite consequences, so the difference is measured, not guessed: the same endpoints
are called with a LIVE mega-cap (AAPL) and a LIVE micro-cap, then with the delisted names.

Also: what does the free delisted-companies list actually CONTAIN? A list of names is worthless if
it carries no delisting DATE, no exchange, and no way to join it to prices.

Output: demo x/out/y3_fmp_scope.json
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


def call(k: str, path: str, **params) -> dict:
    try:
        r = requests.get(f"{BASE}/{path}", params={**params, "apikey": k}, timeout=30)
        j = None
        try:
            j = r.json()
        except Exception:  # noqa: BLE001
            pass
        n = len(j) if isinstance(j, list) else (len(j.get("historical", [])) if isinstance(j, dict) else None)
        return {"http": r.status_code, "n": n, "head": (r.text[:160] if r.status_code != 200 else None), "json": j}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"{type(exc).__name__}"}


def main() -> None:
    k = key()
    if not k:
        print("CREDENTIAL-GATED: no FMP_API_KEY")
        return

    doc: dict = {
        "id": "RR-Y3-001 part 3 -- FMP free-tier scope: is 402 about the ENDPOINT or the SYMBOL?",
        "why_it_matters": (
            "if the endpoint is paid, the free tier is useless for any backtest. If only DELISTED "
            "symbols are paid, the free tier serves the survivors and hides the casualties -- "
            "which is survivorship bias sold as a free tier. Opposite consequences; measured, not "
            "guessed."
        ),
    }

    # ---- (1) endpoint vs symbol: same calls, live vs delisted ----
    symbols = {
        "AAPL (live mega-cap)": "AAPL",
        "GAIA (live micro-cap)": "GAIA",
        "INFIQ (delisted, Ch.11)": "INFIQ",
        "MIMO (delisted, Ch.11)": "MIMO",
    }
    matrix = {}
    for label, sym in symbols.items():
        row = {}
        for ep, extra in (
            ("quote", {}),
            ("historical-price-eod/full", {}),
            ("income-statement", {"limit": 4}),
            ("profile", {}),
        ):
            r = call(k, ep, symbol=sym, **extra)
            row[ep] = {"http": r.get("http"), "n": r.get("n"), "head": r.get("head")}
            time.sleep(0.4)
        matrix[label] = row
        print(f"  {label:<26} " + "  ".join(
            f"{ep.split('/')[0][:9]}={row[ep]['http']}/{row[ep]['n']}" for ep in row
        ), flush=True)
    doc["endpoint_vs_symbol_matrix"] = matrix

    # ---- (2) what is IN the free delisted-companies list? ----
    dl = call(k, "delisted-companies", page=0)
    sample = dl.get("json")[:5] if isinstance(dl.get("json"), list) else None
    doc["delisted_companies_list"] = {
        "http": dl.get("http"),
        "n_on_page_0": dl.get("n"),
        "fields_present": sorted(sample[0].keys()) if sample else None,
        "sample_rows": sample,
        "reading": (
            "a delisted-companies LIST is only useful if it carries a delisting DATE and joins to "
            "prices. Fields shown above; judge for yourself."
        ),
    }
    print(f"\n  delisted-companies: http={dl.get('http')} n={dl.get('n')} "
          f"fields={sorted(sample[0].keys()) if sample else None}", flush=True)

    # ---- (3) does the free list cover OUR EDGAR-confirmed casualties? ----
    ours = {"ALFI", "INFI", "MIMO", "SFT", "SI", "ARDS", "RBT", "DNMR", "WINS", "VINC",
            "ALFIQ", "INFIQ", "MIMOQ", "SFTGQ", "SICP", "RBTC", "WINSF"}
    hit, pages = {}, 0
    for p in range(6):  # free tier: keep it small
        r = call(k, "delisted-companies", page=p)
        if r.get("http") != 200 or not isinstance(r.get("json"), list) or not r["json"]:
            break
        pages += 1
        for row in r["json"]:
            s = row.get("symbol")
            if s in ours:
                hit[s] = row
        time.sleep(0.4)
    doc["coverage_of_our_edgar_sample"] = {
        "pages_scanned": pages,
        "our_tickers": sorted(ours),
        "found_in_list": hit,
        "n_found": len(hit),
        "caveat": (
            "only the first few pages were scanned (free tier). A miss here is NOT proof of "
            "absence from the full list -- it is proof that the list is not trivially joinable."
        ),
    }
    print(f"  our EDGAR casualties found in {pages} scanned pages: {len(hit)}", flush=True)

    (OUT / "y3_fmp_scope.json").write_text(
        json.dumps(doc, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )
    print(f"\nwrote {OUT / 'y3_fmp_scope.json'}")


if __name__ == "__main__":
    main()
