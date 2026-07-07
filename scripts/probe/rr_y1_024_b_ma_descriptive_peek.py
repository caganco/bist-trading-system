"""RR-Y1-024-B — M&A / tender-offer descriptive peek (read-only, return-blind, look-ahead-safe).

NOT a Stage-0, NOT an edge measurement, NO verdict. Descriptive distributions only (median/IQR),
to cheaply test the single biggest threat to an M&A candidate BEFORE any price-parse engineering:
is the event already priced-out (index-reconstitution-relative), or is there a spread/drift?

Regulatory calibration (SPK II-26.1), TWO distinct dates kept separate:
  t0 = control-change / sale-agreement public announcement  (the information event; jump here)
  t1 = formal mandatory-tender-offer start                  (info-form approval; weeks-months after t0)
Call price is based on the pre-announcement 6-month VWAP, so the spread can be + or -.
Windows are BUSINESS-DAY based (aligned to the panel's own trading calendar).

DISC-10 compliance: windows are EX-ANTE FIXED business-day offsets; NO ex-post peak/trough
selection; every per-window metric uses only prices inside its fixed window; entry is dated at
t0/t1 (known at that time), so the cumulative-return metric is look-ahead-safe.

This computes EVENT-WINDOW cumulative price changes purely as a DESCRIPTIVE characterisation of
the announcement, not as a strategy P&L (no holding rule, no cost, no position, no verdict).
"""
from __future__ import annotations

import datetime as _dt
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kap_bycriteria_client as kap  # noqa: E402

PANEL = "data/clean_universe/adjusted_prices_2019_2026.parquet"
XU100 = "data/snapshots/exposure_d187_xu100.parquet"
YEARS = range(2019, 2027)

TENDER_SUBJ = "pay alım teklifi yoluyla"          # formal offer (t1)
SQUEEZE_CUES = ("ortaklıktan çık", "satma hakk")   # squeeze-out / sell-out
T0_CUES = ("birleş", "devral", "pay devri", "hisse devri", "hâkim ortak", "hakim ortak",
           "yönetim kontrol", "satın al", "pay satış", "kontrol değiş")
EPISODE_GAP_D = 60          # disclosures on a ticker within 60 calendar days = one episode
T0_LOOKBACK_BD = 180        # search this many business days before t1 for a t0 control-cue


def _pubdate(rec: dict) -> _dt.date | None:
    s = str(rec.get("publishDate", ""))
    try:
        return _dt.datetime.strptime(s.split()[0], "%d.%m.%Y").date()
    except (ValueError, IndexError):
        return None


def load_events() -> list[dict]:
    out = []
    for y in YEARS:
        try:
            recs = kap.fetch_year(y)
        except Exception as e:  # noqa: BLE001
            print(f"  year {y}: fetch error {type(e).__name__}", file=sys.stderr)
            continue
        for r in recs:
            subj = str(r.get("subject", "")).lower()
            summ = str(r.get("summary", "")).lower()
            d = _pubdate(r)
            if d is None:
                continue
            kind = None
            if TENDER_SUBJ in subj:
                kind = "tender_t1"
            elif any(c in subj or c in summ for c in SQUEEZE_CUES):
                kind = "squeeze"
            elif any(c in subj or c in summ for c in T0_CUES):
                kind = "control_t0"
            if kind:
                out.append({"date": d, "subject": r.get("subject"),
                            "stocks": (r.get("stockCodes") or ""), "kind": kind})
    return out


def panel_calendar() -> tuple[pd.DataFrame, pd.Series, list[_dt.date]]:
    df = pd.read_parquet(PANEL)
    df["date"] = pd.to_datetime(df["date"])
    px = df.pivot_table(index="date", columns="symbol", values="adjusted_close")
    xu = pd.read_parquet(XU100)
    xcol = "close" if "close" in xu.columns else xu.select_dtypes("number").columns[0]
    if "date" in xu.columns:
        xu = xu.set_index(pd.to_datetime(xu["date"]))
    xser = xu[xcol].reindex(px.index).ffill()
    cal = list(px.index.date)
    return px, xser, cal


def _bd_index(cal: list[_dt.date], d: _dt.date) -> int | None:
    """First trading day on/after d -> its position in the calendar."""
    lo, hi = 0, len(cal)
    while lo < hi:
        mid = (lo + hi) // 2
        if cal[mid] < d:
            lo = mid + 1
        else:
            hi = mid
    return lo if lo < len(cal) else None


def cumret(series: pd.Series, i0: int, a: int, b: int) -> float | None:
    """Cumulative simple return over window [i0+a, i0+b] (business-day offsets)."""
    s, e = i0 + a, i0 + b
    if s < 0 or e >= len(series):
        return None
    p0, p1 = series.iloc[s], series.iloc[e]
    if not (np.isfinite(p0) and np.isfinite(p1)) or p0 <= 0:
        return None
    return float(p1 / p0 - 1.0)


def dist(xs: list[float]) -> dict:
    a = np.array([x for x in xs if x is not None], float)
    if a.size == 0:
        return {"n": 0}
    return {"n": int(a.size), "median_pct": round(float(np.median(a)) * 100, 2),
            "iqr_pct": [round(float(np.percentile(a, 25)) * 100, 2),
                        round(float(np.percentile(a, 75)) * 100, 2)]}


WINDOWS = {"pre[t-5,t-1]": (-5, -1), "ann[t0,t+1]": (0, 1), "post[t+2,t+20]": (2, 20)}


def main() -> None:
    ev = load_events()
    px, xu, cal = panel_calendar()
    panel_syms = set(px.columns)

    # collapse tender disclosures to episodes (per ticker, gap-based); t1 = first offer date
    tender = sorted([e for e in ev if e["kind"] == "tender_t1"], key=lambda e: e["date"])
    episodes = []  # (ticker, t1)
    last = {}
    for e in tender:
        for tk in [s.strip() for s in e["stocks"].split(",") if s.strip()]:
            if tk not in last or (e["date"] - last[tk]).days > EPISODE_GAP_D:
                episodes.append({"ticker": tk, "t1": e["date"]})
            last[tk] = e["date"]

    on_panel = [ep for ep in episodes if ep["ticker"] in panel_syms]
    # t0 detection: earliest control-cue disclosure for same ticker in [t1-180bd, t1-1]
    ctrl_by_tk = {}
    for e in ev:
        if e["kind"] == "control_t0":
            for tk in [s.strip() for s in e["stocks"].split(",") if s.strip()]:
                ctrl_by_tk.setdefault(tk, []).append(e["date"])
    both = 0
    gaps = []
    for ep in on_panel:
        i1 = _bd_index(cal, ep["t1"])
        cand = [d for d in ctrl_by_tk.get(ep["ticker"], [])
                if i1 is not None and 0 < (i1 - (_bd_index(cal, d) or i1)) <= T0_LOOKBACK_BD]
        if cand:
            ep["t0"] = min(cand)
            both += 1
            gaps.append((ep["t1"] - ep["t0"]).days)

    # window distributions centered on t1 (always defined) and t0 (where defined)
    def windows_for(center_key: str) -> dict:
        res = {}
        for wname, (a, b) in WINDOWS.items():
            raw, rel = [], []
            for ep in on_panel:
                d = ep.get(center_key)
                if d is None:
                    continue
                i0 = _bd_index(cal, d)
                if i0 is None:
                    continue
                r = cumret(px[ep["ticker"]], i0, a, b)
                m = cumret(xu, i0, a, b)
                raw.append(r)
                rel.append(r - m if (r is not None and m is not None) else None)
            res[wname] = {"raw": dist(raw), "xu100_relative": dist(rel)}
        return res

    # tradability of the on-panel tender targets (ADV trailing 252 bd before t1)
    dfv = pd.read_parquet(PANEL, columns=["date", "symbol", "value_tl"])
    dfv["date"] = pd.to_datetime(dfv["date"])
    advs = []
    for ep in on_panel:
        g = dfv[(dfv["symbol"] == ep["ticker"]) & (dfv["date"] < pd.Timestamp(ep["t1"]))].tail(252)
        if len(g) >= 20:
            advs.append(float(g["value_tl"].mean()))
    advs = np.array(advs, float)

    report = {
        "DISC10": "windows ex-ante fixed business-day offsets; no ex-post peak/trough selection; "
                  "metrics look-ahead-safe (entry dated at t0/t1).",
        "tender_disclosures_raw": len(tender),
        "tender_episodes_total": len(episodes),
        "tender_episodes_on_panel": len(on_panel),
        "episodes_with_detectable_t0": both,
        "t0_t1_gap_days": ({"n": len(gaps), "median": int(np.median(gaps)),
                            "iqr": [int(np.percentile(gaps, 25)), int(np.percentile(gaps, 75))]}
                           if gaps else {"n": 0}),
        "windows_centered_t1": windows_for("t1"),
        "windows_centered_t0": windows_for("t0"),
        "tradability_on_panel": {
            "n_with_adv": int(advs.size),
            "median_adv_tl": round(float(np.median(advs)), 0) if advs.size else None,
            "adv_ge_5M_pct": round(100 * float((advs >= 5e6).mean()), 1) if advs.size else None,
            "adv_ge_25M_pct": round(100 * float((advs >= 25e6).mean()), 1) if advs.size else None,
            "adv_ge_100M_pct": round(100 * float((advs >= 100e6).mean()), 1) if advs.size else None,
        },
        "off_panel_episodes": len(episodes) - len(on_panel),
        "call_spread": "PARSE-NEEDED — call price is not a top-level byCriteria field "
                       "(lives in the tender-offer attachment form); not forced.",
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
