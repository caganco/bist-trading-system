"""RR-Y1-026 — Cross-venue lead-lag descriptive peek (read-only, return-blind, look-ahead-safe).

NOT a Stage-0, NOT an edge measurement, NO verdict. Descriptive correlation only, to answer one
structural question: a US-traded Turkey instrument moves while BIST is closed -> does that move
predict BIST's next session, and is the relationship in the OVERNIGHT GAP (efficient, not
retail-harvestable) or in the POST-OPEN DRIFT (potentially harvestable)?

Time arrow (DISC-10, look-ahead-safe, timezone-aligned):
  BIST session b0 closes ~18:00 TR. The US session on b0's calendar date runs ~16:30-23:00 TR
  (mostly AFTER the BIST close) and ends well before BIST session b1 opens ~10:00 TR next day.
  US SIGNAL = US intraday return Open->Close on the last US session in [b0.date, b1.date)
  -> known BEFORE b1's open. Tested against:
    (a) BIST overnight gap : Open(b1)/Close(b0) - 1
    (b) BIST post-open      : Close(b1)/Open(b1) - 1
  Windows are ex-ante fixed; no ex-post peak/trough selection.

These are descriptive correlations of price changes, not a strategy P&L (no position, cost, or
holding rule, no verdict). DISC-13: yfinance public data only, no credential.
"""
from __future__ import annotations

import json
import warnings

import numpy as np
import pandas as pd
import yfinance as yf
from scipy import stats

warnings.filterwarnings("ignore")

START = "2018-01-01"


def ohlc(ticker: str) -> pd.DataFrame:
    df = yf.download(ticker, start=START, progress=False, auto_adjust=False)
    if df is None or len(df) == 0:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    out = df[["Open", "Close"]].dropna()
    out.index = pd.to_datetime(out.index).normalize()
    return out


def leadlag(us: pd.DataFrame, bist: pd.DataFrame) -> dict:
    """US intraday(Open->Close) -> next-BIST gap & post-open, look-ahead-safe aligned."""
    us_intra = (us["Close"] / us["Open"] - 1.0).dropna()       # purely the US session
    us_intra.index = us_intra.index.normalize()
    bdates = list(bist.index)
    rows = []
    for i in range(1, len(bdates)):
        b0, b1 = bdates[i - 1], bdates[i]
        win = us_intra[(us_intra.index >= b0) & (us_intra.index < b1)]   # US session(s) between
        if win.empty:
            continue
        sig = float(win.iloc[-1])                                        # last US close before b1 open
        c0, o1, c1 = bist.loc[b0, "Close"], bist.loc[b1, "Open"], bist.loc[b1, "Close"]
        if not (c0 > 0 and o1 > 0):
            continue
        rows.append((sig, o1 / c0 - 1.0, c1 / o1 - 1.0))
    if len(rows) < 30:
        return {"n": len(rows), "note": "insufficient"}
    a = np.array(rows, float)
    sig, gap, post = a[:, 0], a[:, 1], a[:, 2]

    def rel(x, y):
        pr, pp = stats.pearsonr(x, y)
        sr, sp = stats.spearmanr(x, y)
        beta = float(np.polyfit(x, y, 1)[0])
        return {"pearson_r": round(pr, 3), "pearson_p": round(pp, 4),
                "spearman_rho": round(sr, 3), "beta": round(beta, 3)}

    # asymmetry: large-|US-move| tercile vs small-|US-move| tercile
    absrank = np.argsort(np.abs(sig))
    k = len(sig) // 3
    big, small = absrank[-k:], absrank[:k]
    return {
        "n": len(rows),
        "gap_overnight": rel(sig, gap),
        "post_open_drift": rel(sig, post),
        "fullday_for_ref": rel(sig, (1 + gap) * (1 + post) - 1),
        "asymmetry_large_move_tercile": {
            "n": int(k),
            "gap_pearson_r": round(float(stats.pearsonr(sig[big], gap[big])[0]), 3),
            "post_pearson_r": round(float(stats.pearsonr(sig[big], post[big])[0]), 3),
        },
        "asymmetry_small_move_tercile": {
            "n": int(k),
            "gap_pearson_r": round(float(stats.pearsonr(sig[small], gap[small])[0]), 3),
            "post_pearson_r": round(float(stats.pearsonr(sig[small], post[small])[0]), 3),
        },
        "share_of_signal_in_gap": (
            round(float(np.std(gap) * abs(stats.pearsonr(sig, gap)[0]) /
                        (np.std(gap) * abs(stats.pearsonr(sig, gap)[0])
                         + np.std(post) * abs(stats.pearsonr(sig, post)[0]) + 1e-12)), 3)),
    }


def main() -> None:
    feeds = {t: ohlc(t) for t in ["TUR", "TKC", "XU100.IS", "TCELL.IS"]}
    cov = {t: ({"n": len(df), "from": str(df.index.min().date()), "to": str(df.index.max().date())}
               if len(df) else {"n": 0}) for t, df in feeds.items()}
    report = {
        "DISC10": "US signal = intraday Open->Close on last US session before BIST open; "
                  "ex-ante fixed windows; look-ahead-safe; timezone-aligned (US after BIST close).",
        "coverage": cov,
        "TUR_to_XU100_marketwide": leadlag(feeds["TUR"], feeds["XU100.IS"]),
        "TKC_to_TCELL_dual_listed": leadlag(feeds["TKC"], feeds["TCELL.IS"]),
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
