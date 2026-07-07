# RR-Y1-026 — Cross-venue / cross-listing lead-lag betimsel-peek

**Sınıf:** Cross-venue lead-lag feasibility + betimsel-peek. **Stage-0-DEĞİL**, ölçüm-DEĞİL,
edge-iddiası-DEĞİL, **HÜKÜM-VERMEZ**. Strateji-P&L yok; yalnız **lead-lag-VARLIĞI + hasat-
edilebilirlik** betimsel-korelasyonu (gap vs post-gap-drift AYRI). **Fork yok.** Evren-B'nin son
Tier-1 adayı (Kanal-2): likit-büyük-cap, KAP-bağımsız, yapısal-zaman-gecikmesi mekanizması.

**Soru:** BIST-kapalıyken US-işlem-gören Türkiye-enstrümanlarının hareketi BIST-ertesi-açılışını
öngörür-mü, ve **HASAT-EDİLEBİLİR-mi** (açılış-sonrası-drift'e-taşar) yoksa **gap-tamamen-fiyatlıyor-mu**
(efficient, hasat-edilemez)?

**DISC-10 uyumu (açık):** US-sinyali = BIST-açılışından-önceki son US-session'ın **içgün
(Open→Close)** getirisi — BIST-kapanışından sonra, BIST-açılışından önce → **look-ahead-safe**;
pencereler **ex-ante-sabit**; **timezone-hizalı** (US-session BIST-kapanışından sonra). Betimsel
korelasyon, strateji-P&L değil.

---

## §0 — FEASIBILITY (DISC-12/13: ölçüldü, public yfinance)

| Enstrüman | Kapsam | Medyan günlük $-hacim | Statü |
|---|---|---|---|
| **TUR** (iShares MSCI Turkey ETF, NASDAQ) | 2018-01→2026-06 (n=2124) | **≈$7.3M** | ✅ likit · Türkiye-geneli, US-saatlerinde |
| **TKC** (Turkcell ADR, NYSE) | 2018-01→2026-06 (n=2124) | **≈$2.4M** | ✅ likit · TCELL.IS ile dual-listed |
| XU100.IS / TCELL.IS (BIST) | 2018→2026, OHLC (Open mevcut) | ₺33tn / ₺457M | ✅ karşı-bacak |
| AKBTY (Akbank ADR) · TKGBY (Garanti ADR) | var | **≈$33K / $30K** | ❌ ölü-OTC (kullanılamaz) |
| ISBTY · TKGZ | — | — | ❌ delisted/yok |

→ **Cross-venue likit-evren = yalnız TUR (geneli) + TKC (dual-listed)**. Diğer Türk-ADR'ler ölü-OTC.
Veri public-yfinance ile çekilebilir; tüm-enstrümanlarda Open mevcut (gap hesaplanabilir).
Timezone: US-session(d) ≈16:30-23:00 TR (BIST-kapanış 18:00 sonrası) → BIST-açılış(d+1) ≈10:00 TR.

## §1 — Lead-lag ölçümü (betimsel, gap vs post-open AYRI)

US-içgün-sinyali(t) → BIST-ertesi: **(a) overnight-gap** = Open(b1)/Close(b0)−1 · **(b) post-open**
= Close(b1)/Open(b1)−1.

**TUR → XU100 (market-wide, N=2038):**
| İlişki | Pearson r | Spearman | beta |
|---|---|---|---|
| **(a) overnight-gap** | **+0.238** (p≈0) | +0.283 | +0.132 |
| **(b) post-open-drift** | **−0.103** (p≈0) | +0.034 | −0.114 |
| (ref) full-day | +0.014 (p=0.52, NS) | +0.135 | +0.017 |

**TKC → TCELL (dual-listed, isim-spesifik, N=2059):**
| İlişki | Pearson r | Spearman | beta |
|---|---|---|---|
| **(a) overnight-gap** | **+0.169** (p≈0) | +0.145 | +0.108 |
| **(b) post-open-drift** | **−0.011** (p=0.63, **NS≈0**) | +0.042 | −0.015 |
| (ref) full-day | +0.059 | +0.090 | +0.089 |

**KRİTİK-AYRIM (cevap):** Lead-lag **VAR ve gap'te güçlü** (TUR→XU100 gap r=0.24; TKC→TCELL gap
r=0.17, ikisi de p≈0) — ama **gap'te TÜKENİYOR**: post-open-drift TKC'de **≈0** (r=−0.01, NS),
XU100'de **hafif-NEGATİF** (r=−0.10; açılışta aşırı-tepki sonra içgün geri-dönüş). Full-day-r ≈0
→ sinyal açılış-gap'ine yansıyor, sonrasında taşınmıyor/kısmen-reverse. = **efficient, gap-fiyatlıyor,
post-open hasat-edilemez** (ZPX30-frustrasyonuyla aynı desen; index-recon "priced-at-announcement" akrabası).

## §2 — Asimetri / rejim (büyük US-hareketleri)

| Tercil | TUR→XU100 gap r | TUR→XU100 post r | TKC→TCELL gap r | TKC→TCELL post r |
|---|---|---|---|---|
| **büyük-\|US-move\|** (üst-tercil) | **+0.279** | −0.176 | **+0.232** | −0.018 |
| küçük-\|US-move\| (alt-tercil) | +0.054 | +0.012 | +0.021 | +0.048 |

→ Lead-lag **büyük US-hareketlerinde belirgin-güçleniyor** (gap r 0.05→0.28 / 0.02→0.23) — gece-
şok-tipi asimetrik-olaylarda gap-tepkisi en-güçlü. AMA güçlenen kısım **yine gap'te**; XU100'de
büyük-harekette post-open **daha-negatif** (−0.18 = açılış-aşırı-tepki düzeltmesi). Hasat-edilebilir
post-drift büyük-harekette de yok.

## §3 — TCELL↔TKC dual-listed (isim-spesifik temiz test)

Aynı-şirket, iki-venue → genel-risk değil isim-spesifik lead-lag. Sonuç §1'de: gap r=0.169 (gerçek,
p≈0) ama **post-open r=−0.011 (NS, tam-sıfır)** → isim-spesifik sinyalin **%88'i gap'te** tükeniyor,
açılış-sonrası sıfır-drift. Dual-listed kanalda priced-out market-wide'dan da temiz.

---

## NET CÜMLE (öneri-içermez)

Cross-venue lead-lag **VAR ve istatistiksel-güçlü ama overnight-gap'te fiyatlanıyor**: TUR→XU100
gap-r=+0.24 / TKC→TCELL gap-r=+0.17 (p≈0, büyük US-hareketlerinde gap-r 0.23-0.28'e çıkar), ancak
**post-open-drift'e taşınmıyor** (TKC post-r=−0.01 NS; XU100 post-r=−0.10, hafif-reversal) → ilişki
**efficient/gap-fiyatlı, açılış-sonrası hasat-edilemez** (detection ≠ monetization). HÜKÜM yok.

---

## Caveat'lar
- Yalnız lead-lag-varlığı + gap-vs-post betimsel-korelasyonu — getiri/edge/strateji-P&L ölçülmedi (tasarım-gereği).
- **Günlük OHLC** (yfinance); açılış-sonrası ilk-dakikalardaki hızlı-decay intraday-veri-yok → ölçülmedi
  (post-open = tam Open→Close). Açılış-içi mikro-yapı ayrı.
- **BIST-Open kalitesi:** yfinance açılış-fiyatı açılış-seansı/ilk-trade olabilir; stale-open gap'i
  yanlı-küçültür. Güçlü gap-r (0.17-0.24) Open'ın gerçek olduğunu düşündürür ama mikro-yapı-gürültüsü
  (açılış-auction, bid-ask-bounce) post-open-reversal'in bir kısmını açıklayabilir.
- TUR ≈ MSCI-Turkey (büyük-BIST-isimleri) → US-saatlerinde Türkiye-risk-repricing proxy'si; lead-lag
  "gece Türkiye-riski yeniden-fiyatlama → BIST-açılış" mekanizması.
- Korelasyon ≠ tradability: gap'i yakalamak açılış-auction'da işlem gerektirir (retail-güç); post-open
  zaten sıfır/negatif. Bu peek **hasat-edilebilirliği betimler, hüküm-vermez**.
- DISC-10: ex-ante-sabit pencereler, ex-post-seçim-yok, look-ahead-safe, timezone-hizalı. Fork maintainer'a.

Kaynaklar (read-only, public): yfinance TUR/TKC/XU100.IS/TCELL.IS günlük OHLC ·
prob-script `scripts/probe/rr_y1_026_cross_venue_leadlag.py` (betimsel-korelasyon-only, DISC-10-guarded).
Dış-bağlam: ADR/ETF lead-lag literatürü (gap genelde fiyatlar); RR-Y1-011-E/index_recon (priced-at-
announcement / detection-not-monetization deseni — bu peek onu yankılar).
