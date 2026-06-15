"""RR-Y1-023 — Behavioral-universe x instrument-accessibility intersection probe.

Read-only, return-blind feasibility measurement. NOT a Stage-0, NOT a measurement of
any edge, NO strategy is run, NO holding/forward/event return or CAR is computed.

It answers one structural question: does the place where behavioural alpha would live
(speculative / high-volatility / illiquid / small names) overlap with the place where a
*negative* view is expressible on BIST (short-sale-eligible, single-stock-futures)?

What is computed (all descriptive, cross-sectional universe characteristics, not P&L):
  * per-symbol average daily traded value (ADV, liquidity)
  * per-symbol trailing annualised realised volatility   (universe-defining sort key)
  * per-symbol trailing max daily return                 (lottery / MAX proxy, Bali 2011)
  * point-in-time BIST-30 / BIST-100 index membership
  * instrument-accessibility flags per name: short-sale-eligible, SSF underlying
Output: per-universe negative-view-expressible-% (name-weighted AND ADV-weighted) and
long-expressible-% at several liquidity thresholds, plus the A-vs-B two-way table.

Data sources (public DataStore products, offline canonical archive; read-only):
  * short-sale eligibility/activity : data/bist_datastore_archive/short_selling/
                                      PP_ACIGASATIS / acigasat monthly bulletins
  * single-stock futures (SSF)      : data/bist_datastore_archive/viop/
                                      VIOP_GUNSONU_FIYATHACIM main series (segment SSF)
  * universe / liquidity / index    : data/clean_universe/adjusted_prices_2019_2026.parquet

Warrant issuer/underlying list and per-stock securities-lending (SLB/OPP) balances have
no offline archive in this repo -> reported as feasibility-blocked (not assumed).

Counts/flags only; no return/pct_change is computed on any holding or event window
(DEC-053-safe). Raw scraped bulletins are not committed (only this script + derived RR doc).
"""
from __future__ import annotations

import glob
import gzip
import io
import json
import os
import re
import warnings
import zipfile

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ARCH = "data/bist_datastore_archive"
PANEL = "data/clean_universe/adjusted_prices_2019_2026.parquet"

# Frozen calendar window for instrument-accessibility (chosen without looking at results):
# trailing 24 months ending at the panel's last month.
SS_WIN_LO, SS_WIN_HI = "202406", "202605"
LIQ_THRESHOLDS_TL = (5e6, 25e6, 100e6)  # meaningful-position liquidity band

_TICK = re.compile(r"^([A-Z0-9]{3,6})\.E$")


def _ym(path: str) -> str | None:
    m = re.search(r"(\d{6})", os.path.basename(path))
    return m.group(1) if m else None


def _read_viop(path: str) -> list[str]:
    if path.endswith(".gz"):
        return gzip.open(path, "rt", encoding="windows-1254", errors="replace").read().splitlines()
    return open(path, encoding="windows-1254", errors="replace").read().splitlines()


def ssf_underlyings(n_recent: int = 24) -> set[str]:
    """Distinct equity single-stock-futures underlyings over the last n monthly files."""
    files = sorted(glob.glob(f"{ARCH}/viop/VIOP_GUNSONU_FIYATHACIM.M.*.csv"))[-n_recent:]
    out: set[str] = set()
    for f in files:
        raw = _read_viop(f)
        if not raw:
            continue
        cols = [c.strip() for c in raw[0].split(";")]
        try:
            seg, und, sinif = (cols.index("PAZAR SEGMENTI"),
                               cols.index("DAYANAK VARLIK"),
                               cols.index("SOZLESME SINIFI"))
        except ValueError:
            continue
        for line in raw[2:]:
            p = line.split(";")
            if len(p) <= und:
                continue
            if p[seg].strip() == "SSF" or p[sinif].strip() == "D_EQ_FPD":
                base = p[und].strip().split(".")[0].strip()
                if base.isalpha() and 3 <= len(base) <= 6:
                    out.add(base)
    return out


def warrant_put_underlyings(ticker_set: set[str], min_monthly_val_tl: float = 1e6) -> dict:
    """Single-stock PUT-warrant underlyings from the latest full daily bulletin.

    Equity warrant groups in PP_GUNSONUFIYATHACIM: ECW = equity call warrant,
    EPW = equity put warrant. The instrument short-name (BULTEN ADI) is prefixed by the
    underlying code; index/commodity/FX warrants (XAU, BRENT, XU030, DAX, ...) do not match
    an equity ticker and are excluded. Returns the set of equity underlyings that carry a
    PUT warrant whose monthly traded value clears the liquidity floor (dead quotes excluded).
    """
    files = sorted(glob.glob(f"{ARCH}/prices_official/PP_GUNSONUFIYATHACIM.M.*.csv"))
    if not files:
        return {"all_put": set(), "liquid_put": set(), "monthly_val": {}}
    raw = open(files[-1], encoding="windows-1254", errors="replace").read().splitlines()
    cols = {c.strip(): i for i, c in enumerate(raw[0].split(";"))}
    g_i, nm_i, vol_i = cols["ENSTRUMAN GRUBU"], cols["BULTEN ADI"], cols["TOPLAM ISLEM HACMI"]
    tickers = sorted((t for t in ticker_set if len(t) >= 4), key=len, reverse=True)
    put_val: dict[str, float] = {}

    def _match(name: str) -> str | None:
        for t in tickers:
            if name.startswith(t):
                nxt = name[len(t):len(t) + 1]
                if nxt in ("C", "P", "S", "T", "V") or nxt.isdigit():
                    return t
        return None

    for line in raw[2:]:
        p = line.split(";")
        if len(p) <= vol_i or p[g_i].strip() != "EPW":
            continue
        u = _match(p[nm_i].strip())
        if u is None:
            continue
        try:
            v = float(p[vol_i]) if p[vol_i].strip() else 0.0
        except ValueError:
            v = 0.0
        put_val[u] = put_val.get(u, 0.0) + v
    liquid = {u for u, v in put_val.items() if v >= min_monthly_val_tl}
    return {"all_put": set(put_val), "liquid_put": liquid, "monthly_val": put_val}


def _parse_short_month(path: str) -> set[str]:
    """Short-sale-eligible/active tickers in one monthly bulletin (csv or xlsx)."""
    z = zipfile.ZipFile(path)
    main = sorted(z.namelist(), key=lambda n: z.getinfo(n).file_size, reverse=True)[0]
    out: set[str] = set()
    if main.lower().endswith(".xlsx"):
        xl = pd.read_excel(io.BytesIO(z.read(main)), header=None)
        for _, r in xl.iterrows():
            m = _TICK.match(str(r.iloc[0]).strip())
            if m:
                out.add(m.group(1))
    else:
        for line in z.read(main).decode("windows-1254", errors="replace").splitlines():
            p = line.split(";")
            if not p:
                continue
            c0 = p[0].strip()
            if _TICK.match(c0):
                out.add(_TICK.match(c0).group(1))
            elif re.match(r"^[A-Z]{3,6}$", c0) and c0 not in ("PAY", "EQUITY") and len(p) > 3:
                out.add(c0)
    return out


def short_eligible_by_month() -> dict[str, set[str]]:
    files = sorted((f for f in glob.glob(f"{ARCH}/short_selling/*.zip") if _ym(f)), key=_ym)
    return {_ym(f): _parse_short_month(f) for f in files}


def build_universe_metrics(df: pd.DataFrame) -> pd.DataFrame:
    end = df["date"].max()
    w252 = df[df["date"] > end - pd.Timedelta(days=370)]
    w21 = df[df["date"] > end - pd.Timedelta(days=35)]

    def _m(g: pd.DataFrame) -> pd.Series:
        g = g.sort_values("date")
        r = np.log(g["adjusted_close"] / g["adjusted_close"].shift(1)).dropna()
        return pd.Series({"adv": g["value_tl"].mean(), "vol": r.std() * np.sqrt(252), "n": len(r)})

    m = w252.groupby("symbol").apply(_m)
    m["maxret"] = w21.groupby("symbol").apply(
        lambda g: np.log(g["adjusted_close"] / g["adjusted_close"].shift(1)).max()
    )
    last = df[df["date"] == end].set_index("symbol")[["bist30", "bist100"]]
    m = m.join(last)
    m = m[m["n"] >= 120].copy()
    m["vol_hi"] = m["vol"] >= m["vol"].quantile(2 / 3)
    m["maxret_hi"] = m["maxret"] >= m["maxret"].quantile(2 / 3)
    m["adv_lo"] = m["adv"] <= m["adv"].quantile(1 / 3)
    return m


def coverage(m: pd.DataFrame, names: list[str], short_set: set[str], ssf_set: set[str],
             put_set: set[str] | None = None) -> dict:
    put_set = put_set or set()
    sub = m.loc[[n for n in names if n in m.index]]
    adv = sub["adv"]
    neg = sub.index.to_series().apply(lambda t: t in short_set or t in ssf_set or t in put_set)
    put = sub.index.to_series().isin(put_set)
    res = {
        "n": int(len(sub)),
        "neg_name_pct": round(100 * neg.mean(), 1),
        "neg_adv_pct": round(100 * adv[neg.values].sum() / adv.sum(), 1) if adv.sum() else 0.0,
        "short_name_pct": round(100 * sub.index.to_series().isin(short_set).mean(), 1),
        "ssf_name_pct": round(100 * sub.index.to_series().isin(ssf_set).mean(), 1),
        "liquid_put_warrant_name_pct": round(100 * put.mean(), 1),
        "liquid_put_warrant_adv_pct": round(100 * adv[put.values].sum() / adv.sum(), 1) if adv.sum() else 0.0,
        "median_adv_tl": round(float(adv.median()), 0),
    }
    for thr in LIQ_THRESHOLDS_TL:
        res[f"long_name_pct@{thr/1e6:.0f}M"] = round(100 * (adv >= thr).mean(), 1)
    return res


def main() -> None:
    df = pd.read_parquet(PANEL)
    df["date"] = pd.to_datetime(df["date"])
    end = df["date"].max()

    ssf = ssf_underlyings()
    ss_month = short_eligible_by_month()
    short_union = set().union(
        *[s for m, s in ss_month.items() if SS_WIN_LO <= m <= SS_WIN_HI]
    )

    m = build_universe_metrics(df)
    universe_b = m[m["bist30"] == 1].index.tolist()
    a_broad = m[((m["vol_hi"]) | (m["maxret_hi"]) | (m["adv_lo"])) & (m["bist100"] != 1)].index.tolist()
    a_core = m[(m["vol_hi"]) & (m["maxret_hi"]) & (m["bist100"] != 1)].index.tolist()

    wt = warrant_put_underlyings(set(df["symbol"].unique()))
    liquid_put = wt["liquid_put"]

    # structural check: is negative-view eligibility a subset of the index?
    last = df[df["date"] == end].set_index("symbol")
    neg_all = short_union | ssf | liquid_put
    outside_idx = sorted(t for t in neg_all if t in last.index and last.loc[t, "bist100"] != 1)

    report = {
        "panel_end": str(end.date()),
        "frozen_short_window": f"{SS_WIN_LO}..{SS_WIN_HI}",
        "n_ssf_underlyings": len(ssf),
        "n_short_eligible_union": len(short_union),
        "n_equity_put_warrant_underlyings": len(wt["all_put"]),
        "n_liquid_put_warrant_underlyings": len(liquid_put),
        "neg_eligibility_outside_bist100": outside_idx,
        "short_active_by_month": {k: len(v) for k, v in sorted(ss_month.items()) if k >= "202101"},
        "universe_B_liquid_largecap": coverage(m, universe_b, short_union, ssf, liquid_put),
        "universe_A_broad_speculative": coverage(m, a_broad, short_union, ssf, liquid_put),
        "universe_A_core_lottery": coverage(m, a_core, short_union, ssf, liquid_put),
        "feasibility_blocked": {
            "securities_lending_SLB_OPP": "no offline archive; executed short-sale volume is a joint short+borrow proxy",
        },
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
