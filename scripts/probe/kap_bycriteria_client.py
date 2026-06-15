"""Reusable KAP disclosure client — public, no-auth, read-only.

Solves the KAP access bottleneck shared by the event candidates (M&A / mandatory tender
offer / share-buyback / insider-manager transactions): all are KAP ÖDA (special-disclosure)
events.

Route diagnosis (measured 2026-06-15, this network):
  * `POST /tr/api/memberDisclosureQuery`  -> WAF-TARPITTED (connection accepted, response
    black-holed; 6/6 attempts × 25s timeout, even with warm-up cookies). This is the endpoint
    the legacy `src/data/kap_scraper.py` uses, which is why it reported "often WAF-blocked".
  * `POST /tr/api/disclosure/members/byCriteria` -> WORKS (HTTP 200 in ~0.3s, no auth, only a
    warm-up GET cookie needed). Returns full records: publishDate (PIT), stockCodes,
    relatedStocks, subject (konu), summary, disclosureClass, disclosureIndex (stable id),
    attachmentCount. This is the route used (and cached) by the index-recon work.

Constraints:
  * 2000-record hard cap per query -> adaptive date-bisection (split until each window < cap).
  * The subject-taxonomy GET endpoints 404, so subjectList-OID server filtering is unavailable;
    we post-filter on the clean `subject` text (e.g. "Paylar'ın Geri Alınmasına İlişkin Bildirim").
  * The offer / buyback / squeeze-out PRICE is not a top-level field; it lives in the disclosure
    attachment / detail form (attachmentCount>0) and needs a per-disclosure detail fetch + parse
    (separate engineering, not done here).

DISC-13: public no-auth only; no credential, no WAF bypass beyond the site's own warm-up cookie.
Read-only; this client fetches disclosure METADATA (counts/dates/subjects), computes no returns.
Raw pulls are cached under data/bist_datastore_archive/kap_index_probe/ and are NOT committed.
"""
from __future__ import annotations

import datetime as _dt
import json
import time
from pathlib import Path

import requests

API = "https://www.kap.org.tr/tr/api/disclosure/members/byCriteria"
WARMUP = "https://www.kap.org.tr/tr/bildirim-sorgu"
CAP = 2000
CACHE = Path("data/bist_datastore_archive/kap_index_probe/bycriteria_cache")

# Clean konu (subject) text fragments for the event candidates (post-filter, case-insensitive).
SUBJECT_FILTERS = {
    "buyback": ("paylar", "geri al"),          # "Payların Geri Alınmasına İlişkin Bildirim"
    "insider_mgr": ("pay alım satım bildirim",),  # "Pay Alım Satım Bildirimi" (mgr/insider)
    "tender_ma": ("pay alım teklif", "birleş", "devral", "ortaklıktan çık"),
}


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"),
        "Accept-Language": "tr-TR,tr;q=0.9", "Accept": "application/json",
        "Content-Type": "application/json",
    })
    try:
        s.get(WARMUP, timeout=10)   # WAF warm-up cookie
    except requests.RequestException:
        pass
    return s


def _query(s: requests.Session, fr: str, to: str, disclosure_class: str = "ODA") -> list[dict]:
    body = {"fromDate": fr, "toDate": to, "disclosureClass": disclosure_class, "subjectList": [],
            "mkkMemberOidList": [], "inactiveMkkMemberOidList": [], "bdkMemberOidList": [],
            "fromSrc": False, "disclosureIndexList": []}
    r = s.post(API, json=body, timeout=35)
    r.raise_for_status()
    return r.json()


def fetch_range(fr: _dt.date, to: _dt.date, s: requests.Session | None = None,
                disclosure_class: str = "ODA") -> list[dict]:
    """All ODA disclosures in [fr, to], dedup by disclosureIndex, adaptive-bisecting under the cap."""
    s = s or _session()
    recs = _query(s, fr.isoformat(), to.isoformat(), disclosure_class)
    if len(recs) < CAP or fr >= to:
        return recs
    mid = fr + (to - fr) // 2                                   # cap hit -> bisect the window
    time.sleep(0.2)
    left = fetch_range(fr, mid, s, disclosure_class)
    right = fetch_range(mid + _dt.timedelta(days=1), to, s, disclosure_class)
    seen, out = set(), []
    for x in left + right:
        i = x.get("disclosureIndex")
        if i not in seen:
            seen.add(i); out.append(x)
    return out


def classify(rec: dict) -> list[str]:
    text = (str(rec.get("subject", "")) + " " + str(rec.get("summary", ""))).lower()
    return [name for name, frags in SUBJECT_FILTERS.items() if any(f in text for f in frags)]


def fetch_year(year: int, cache: bool = True) -> list[dict]:
    CACHE.mkdir(parents=True, exist_ok=True)
    cf = CACHE / f"oda_{year}.json"
    if cache and cf.exists():
        return json.loads(cf.read_bytes())
    recs = fetch_range(_dt.date(year, 1, 1), _dt.date(year, 12, 31))
    if cache:
        cf.write_text(json.dumps(recs, ensure_ascii=False), encoding="utf-8")
    return recs


def main() -> None:
    import argparse
    import collections

    ap = argparse.ArgumentParser()
    ap.add_argument("--years", default="2025", help="comma-separated, e.g. 2024,2025")
    args = ap.parse_args()

    report = {}
    for y in [int(x) for x in args.years.split(",")]:
        recs = fetch_year(y)
        cls = collections.Counter()
        names = collections.defaultdict(set)
        for r in recs:
            for c in classify(r):
                cls[c] += 1
                for sc in (r.get("stockCodes") or "").split(","):
                    if sc.strip():
                        names[c].add(sc.strip())
        report[y] = {"total_oda": len(recs),
                     **{f"{k}_disclosures": cls[k] for k in SUBJECT_FILTERS},
                     **{f"{k}_distinct_names": len(names[k]) for k in SUBJECT_FILTERS}}
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
