"""RR-Y1-024 — M&A / mandatory-tender-offer / squeeze-out event candidate: feasibility proxy.

Read-only, return-blind. NOT a Stage-0, NOT a measurement of any edge; no strategy is run,
no holding/forward/event return or CAR is computed. Two owned, offline things are produced:

  1. A delisting / terminal-corporate-event PROXY from the survivorship-clean panel — count,
     per-year distribution, and liquidity profile. This is a LOWER-BOUND proxy for the
     M&A / squeeze-out target universe: it conflates mergers and squeeze-outs with bankruptcy,
     transfer, and regulatory delisting, so it overstates the count and understates nothing
     about the liquidity skew. It is NOT the M&A/tender-offer event count (that needs the KAP
     disclosure stream, which is not owned in-repo and was WAF/timeout-gated live this session).

  2. (optional, --live) a bounded reachability probe of the public KAP disclosure-query
     endpoint, to record its status as a fact (DISC-12) rather than assume it.

Counts/flags only; no return/pct_change on any holding or event window (DEC-053-safe).
"""
from __future__ import annotations

import sys

import pandas as pd

PANEL = "data/clean_universe/adjusted_prices_2019_2026.parquet"
DELIST_GAP_DAYS = 60          # last-trade earlier than (panel_end - gap) => terminal-event proxy
LIQ_THRESHOLDS_TL = (5e6, 25e6, 100e6)


def delisting_proxy() -> dict:
    df = pd.read_parquet(PANEL)
    df["date"] = pd.to_datetime(df["date"])
    end, start = df["date"].max(), df["date"].min()
    last_dt = df.groupby("symbol")["date"].max()
    delisted = last_dt[last_dt < end - pd.Timedelta(days=DELIST_GAP_DAYS)].index.tolist()

    def _adv(sym: str) -> float:
        g = df[df["symbol"] == sym].sort_values("date").tail(252)
        return float(g["value_tl"].mean())

    adv = pd.Series({s: _adv(s) for s in delisted})
    ever100 = df[df["symbol"].isin(delisted)].groupby("symbol")["bist100"].max()
    yrs = pd.Series({s: last_dt[s].year for s in delisted}).value_counts().sort_index()
    out = {
        "panel": f"{start.date()}..{end.date()}",
        "n_symbols": int(df["symbol"].nunique()),
        "n_terminal_event_proxy": len(delisted),
        "per_year": {int(y): int(c) for y, c in yrs.items()},
        "median_adv_tl": round(float(adv.median()), 0),
        "ever_bist100": int(ever100.sum()),
        "ever_bist100_names": sorted(ever100[ever100 == 1].index.tolist()),
    }
    for thr in LIQ_THRESHOLDS_TL:
        out[f"adv_ge_{thr/1e6:.0f}M_pct"] = round(100 * (adv >= thr).mean(), 1)
    return out


def kap_reachability_probe(timeout_s: float = 30.0) -> dict:
    """Record the public KAP disclosure-query endpoint status as a measured fact (DISC-13: no auth)."""
    import httpx

    ua = {
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8",
        "Origin": "https://www.kap.org.tr",
        "Referer": "https://www.kap.org.tr/tr/bildirim-sorgu",
    }
    url = "https://www.kap.org.tr/tr/api/memberDisclosureQuery"
    body = {"fromDate": "2026-01-01", "toDate": "2026-06-15", "disclosureClass": "ODA",
            "memberType": "IGS", "fromSrc": "N", "subjectList": [], "mkkMemberOidList": []}
    try:
        with httpx.Client(timeout=timeout_s, headers=ua, follow_redirects=True, verify=False) as c:
            r = c.post(url, json=body)
        return {"endpoint": url, "status": r.status_code, "bytes": len(r.text)}
    except Exception as e:  # noqa: BLE001  (we record the failure mode as the finding)
        return {"endpoint": url, "status": f"ERR:{type(e).__name__}"}


def main() -> None:
    import json

    report = {"delisting_proxy": delisting_proxy()}
    if "--live" in sys.argv:
        report["kap_reachability"] = kap_reachability_probe()
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
