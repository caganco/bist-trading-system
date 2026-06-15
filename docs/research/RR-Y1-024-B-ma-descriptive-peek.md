# RR-Y1-024-B — M&A / pay-alım-teklifi betimsel-peek (RR-Y1-024 §3 fill)

**Sınıf:** Betimsel-peek (descriptive). **Stage-0-DEĞİL**, ölçüm-DEĞİL, edge-iddiası-DEĞİL,
**HÜKÜM-VERMEZ**. Hiçbir strateji/getiri/alfa/CAR yok; yalnız olay-penceresi **betimsel
dağılımları** (medyan/IQR). RR-Y1-024 §3'te veri-duvarında ertelenen peek, RR-Y1-025 byCriteria
rotasıyla açıldı. Amaç: fiyat-parse-mühendisliğinden ÖNCE en-büyük-tehdidi (priced-out, mekanik-
flow-akrabası) ucuza-yoklamak. **Fork yok.**

**DISC-10 uyumu (açık):** pencereler **EX-ANTE-SABİT iş-günü** offset'leri; ex-post zirve/dip-
seçimi **YOK**; her pencere yalnız kendi-içindeki fiyatları kullanır; giriş t0/t1'de tarihlenir →
metrik **look-ahead-safe**. Pencere-getirileri olayın **betimsel-karakterizasyonudur**, strateji-
P&L değil (pozisyon/maliyet/holding-kuralı yok).

**MEVZUAT-KALİBRE (II-26.1, iki-ayrı-tarih):** t0 = kontrol-değişimi/anlaşma-duyuru (asıl-bilgi-
olayı); t1 = fiili-pay-alım-teklifi-başlangıcı (bilgi-formu-onayı-sonrası, t0'dan haftalar-aylar-
sonra). Çağrı-fiyatı anons-öncesi-6-ay-VWAP tabanlı → spread +/− olabilir.

---

## §0 — Veri-kapsamı (DÜRÜST sınır)

byCriteria (RR-Y1-025) ile ODA çekildi; **bulk-backfill KAP-WAF kümülatif rate-limit'ine çarptı**
→ throttle+backoff eklendi ama oturum-cezası nedeniyle **yalnız 3 yıl indi: 2019, 2020, 2025**
(2021-2024/2026 boş-döndü, poisoned-cache silindi). **Bu PARTIAL bir peek**; tam-peek throttle'lı
çok-oturumlu backfill gerektirir (RR-Y1-025 kalan-mühendislik). Tüm sayılar **indikatif**, N-küçük.

- tender ("Pay Alım Teklifi Yoluyla Pay Toplanması") ham-bildirim: **286** (3 yıl; günlük-tekrarlı)
- episode'a indirgenmiş (ticker × 60g-gap): **35 episode**; **distinct 25 ticker**
- **panel-içi (681 temiz-evren): yalnız 5 ticker** (A1CAP, ARTI, DENIZ, INFO, ISMEN), **9 episode**
- **panel-DIŞI: 26 episode (≈%74)** — mikro-cap, temiz-evrene bile girmiyor

---

## §1 — t0/t1 ayrımı

- 9 panel-içi episode'un **6'sında t0 tespit-edilebildi** (aynı-ticker, t1-öncesi 180-işgünü
  içinde kontrol-cue bildirimi: birleşme/devir/satın-alma/hâkim-ortak/kontrol-değişimi).
- **t0→t1 gap: medyan ≈122 gün** (IQR 86-215 gün) → **mevzuatı doğrular** (fiili-teklif, kontrol-
  olayından ~4 ay sonra). t1 = mekanik/geç-tarih; bilgi t0'da.

## §2 — Pencere-bazlı betimsel dağılım (medyan / IQR)

**t1-merkezli (fiili-teklif, N=7) — priced-out testi:**

| Pencere (işgünü) | Ham medyan | Ham IQR | XU100-rel medyan | XU100-rel IQR |
|---|---|---|---|---|
| pre [t1−5, t1−1] | +0.48% | [−1.01, +2.39] | **−2.06%** | [−4.53, −0.86] |
| anons [t1, t1+1] | −0.35% | [−4.0, +0.94] | **−1.13%** | [−2.42, +1.91] |
| post [t1+2, t1+20] | +9.65% | [+2.09, **+39.59**] | +5.8% | [−2.98, +37.49] |

→ Fiili-teklifte (t1) **pozitif anons-sıçraması YOK** (rel −1.13%) — **priced-out/mekanik
desenle tutarlı** (index-recon-akrabası: teklif önceden-bilinir). post-t1 +9.65% ham **çok-geniş
IQR** (üst +39.59%) → 1-2 isim-kaynaklı, merkezî-eğilim değil; N=7'de okunamaz.

**t0-merkezli (kontrol-olayı, N=3) — ÇOK-KÜÇÜK:** pre rel +0.93% / anons rel −2.34% / post rel
−8.15%. **N=3 yorumlanamaz** (gürültü); yalnız tamlık için kaydedildi.

## §3 — Çağrı-spread

**PARSE-NEEDED.** Çağrı-fiyatı byCriteria top-level-alanı **değil** (teklif-bilgi-formu ek'inde) →
zorlanmadı (DISC-12). priced-out'un kesin-ölçümü bu parse'a bağlı; §2 t1-no-jump bulgusu dolaylı-
gösterge ama spread-değil.

## §4 — Tradability kesişimi (RR-Y1-024 skew testi)

Panel-içi tender-target'ların t1-öncesi 252-işgünü ADV'si: **medyan 2.15M TL**; ADV≥5M **%14.3**,
≥25M **%0.0**, ≥100M **%0.0**. + episode'ların **%74'ü panel-dışı** (mikro-cap). →
**RR-Y1-024'ün mikro-cap-skew'ini TEYİT eder** (red-etmez): tender-target evreni ezici-çoğunlukla
illikit; potansiyel spread/drift olsa-bile likit-olmayan isimlerde.

---

## NET CÜMLE (öneri-içermez)

Betimsel olarak: (a) tender-target'lar **mikro-cap/panel-dışı** (N'den-bağımsız, sağlam — %74
panel-dışı, panel-içi medyan-ADV 2.15M TL, %0 ≥25M); (b) **fiili-teklifte (t1) pozitif anons-
sıçraması yok** (XU100-rel −1.13%), priced-out/mekanik tehditle tutarlı; (c) post-t1 (+9.65% ham,
IQR çok-geniş) ve t0-merkezli (N=3) sinyaller **karakterize-edilemeyecek-kadar-ince**; (d) çağrı-
spread **ek-form-parse gerektirir**. Peek **PARTIAL** (3 yıl: 2019/2020/2025; gerisi WAF-rate-
limit). HÜKÜM yok.

---

## Caveat'lar
- **PARTIAL veri** (3 yıl) + **küçük-N** (9 episode / 7 fiyatlı / 3 t0): §2/§3 **indikatif**, ölçüm-değil.
- t0-tespiti keyword-tabanlı yaklaşık (kontrol-cue subject/summary); gerçek-t0 metin-parse'la kesinleşir.
- post-t1 +9.65% geniş-IQR = isim-kaynaklı; tender-süresince fiyat teklif-fiyatına-pinlenir, ham-getiri yanıltıcı olabilir.
- Çağrı-spread ölçülmedi (top-level-yok); priced-out kesin-hükmü parse'a bağlı.
- DISC-10: ex-ante-sabit iş-günü pencereler, ex-post-seçim-yok, look-ahead-safe. HÜKÜM/fork yok — maintainer'a.

Kaynaklar (repo-içi, read-only): `scripts/probe/rr_y1_024_b_ma_descriptive_peek.py` (betimsel-only,
strateji-P&L-yok, DISC-10-guarded) · `scripts/probe/kap_bycriteria_client.py` (RR-Y1-025 rota) ·
`data/clean_universe/adjusted_prices_2019_2026.parquet` + `exposure_d187_xu100.parquet` (fiyat/endeks).
İlişkili: RR-Y1-024 (M&A feasibility+collision — bu §3'ünü doldurur), RR-Y1-025 (byCriteria erişim),
RR-Y1-011-E/index_recon (priced-at-announcement dersi — t1-no-jump onu yankılar). Ham ODA-pull commit-edilmedi.
