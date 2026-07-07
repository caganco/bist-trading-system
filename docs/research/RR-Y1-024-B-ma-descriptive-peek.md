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

## §0 — Veri-kapsamı

byCriteria (RR-Y1-025) ile ODA çekildi; throttle (`KAP_THROTTLE_S=1.5`) + backoff ile nazik-pace.
**Kapsam: 7/8 yıl — 2019, 2020, 2021, 2022, 2023, 2025, 2026** (kümülatif KAP-WAF rate-limit'i
geçiciydi, resetlendi; nazik-pace yeniden-tetiklemedi). **2024 indirilemedi** (HTTPError;
raise-on-fail ile **temiz-iptal — partial cache'lenmedi**, susarak-eksik-saymadı). N hâlâ
mütevazı → pencere-dağılımları **indikatif**.

- tender ("Pay Alım Teklifi Yoluyla Pay Toplanması") ham-bildirim: **554** (günlük-tekrarlı)
- episode'a indirgenmiş (ticker × 60g-gap): **69 episode**; 
- **panel-içi (681 temiz-evren): yalnız 16 episode** (≈%23); **panel-DIŞI: 53 episode (≈%77)** mikro-cap

---

## §1 — t0/t1 ayrımı

- 16 panel-içi episode'un **13'ünde t0 tespit-edilebildi** (aynı-ticker, t1-öncesi 180-işgünü
  içinde kontrol-cue: birleşme/devir/satın-alma/hâkim-ortak/kontrol-değişimi).
- **t0→t1 gap: medyan ≈128 gün** (IQR 88-244) → **mevzuatı doğrular** (fiili-teklif, kontrol-
  olayından ~4 ay sonra). t1 = mekanik/geç-tarih; bilgi t0'da.

## §2 — Pencere-bazlı betimsel dağılım (medyan / IQR; indikatif)

**t1-merkezli (fiili-teklif, N=12) — priced-out testi:**

| Pencere (işgünü) | Ham medyan | Ham IQR | XU100-rel medyan | XU100-rel IQR |
|---|---|---|---|---|
| pre [t1−5, t1−1] | +0.24% | [−2.22, +3.62] | **−2.58%** | [−3.94, +1.89] |
| anons [t1, t1+1] | +0.64% | [−2.54, +2.33] | **−0.00%** | [−1.43, +2.87] |
| post [t1+2, t1+20] | +4.89% | [−2.82, +22.74] | **−2.95%** | [−6.6, +21.25] |

→ Fiili-teklifte (t1) **anons-sıçraması YOK** (rel ≈0.00%) — **priced-out/mekanik desenle
tutarlı** (index-recon-akrabası). post-t1 XU100-rel **−2.95%** (geniş-IQR) — **pozitif-drift yok**;
(daha-küçük-N=7'deki +5.8% rel **küçük-örnek-artefaktıydı**, fuller-veride kayboldu/negatife-döndü).

**t0-merkezli (kontrol-olayı, N=6) — KÜÇÜK:** pre rel +1.12% / anons rel −0.36% (IQR straddle-0) /
post rel +2.1% (IQR [−5.86,+8.1]). **N=6 hepsi sıfırı-kesiyor** → kontrol-olayında da net-jump-yok
(bu örneklemde); indikatif.

## §3 — Çağrı-spread

**PARSE-NEEDED.** Çağrı-fiyatı byCriteria top-level-alanı **değil** (teklif-bilgi-formu ek'inde) →
zorlanmadı (DISC-12). priced-out'un kesin-ölçümü bu parse'a bağlı; §2 t1-no-jump dolaylı-gösterge.

## §4 — Tradability kesişimi (RR-Y1-024 skew testi)

Panel-içi tender-target'ların t1-öncesi 252-işgünü ADV'si: **medyan 2.33M TL**; ADV≥5M **%25.0**,
≥25M **%0.0**, ≥100M **%0.0**. + episode'ların **%77'si panel-dışı** (mikro-cap). →
**RR-Y1-024'ün mikro-cap-skew'ini güçlü-TEYİT** (7-yıl, N=16): tender-target evreni ezici-çoğunlukla
illikit; potansiyel spread/drift olsa-bile likit-olmayan isimlerde.

---

## NET CÜMLE (öneri-içermez)

Betimsel olarak (7 yıl, 16 panel-içi episode): (a) tender-target'lar **mikro-cap/panel-dışı**
(%77 panel-dışı, panel-içi medyan-ADV 2.33M TL, %0 ≥25M — sağlam, N-bağımsız); (b) **fiili-teklifte
(t1) anons-sıçraması yok** (XU100-rel ≈0.00%) + post-t1 **−2.95% rel** (pozitif-drift yok) →
priced-out/mekanik tehditle tutarlı; (c) t0-merkezli (N=6) net-jump-yok ama çok-ince; (d) çağrı-
spread **ek-form-parse gerektirir**. 2024 indirilemedi (7/8 yıl). HÜKÜM/fork yok.

---

## Caveat'lar
- **Mütevazı-N** (16 panel-içi episode / 12 fiyatlı / 6 t0): §2/§3 **indikatif**, ölçüm-değil.
- 2024 indirilemedi (raise-on-fail temiz-iptal); 7/8 yıl. Diğer yıllar nazik-pace ile tam-indi.
- t0-tespiti keyword-tabanlı yaklaşık (kontrol-cue subject/summary); gerçek-t0 metin-parse'la kesinleşir.
- post-t1 ham-getiri yanıltıcı olabilir (tender-süresince fiyat teklif-fiyatına-pinlenir); XU100-rel daha-anlamlı, o da ≈−3%.
- Çağrı-spread ölçülmedi (top-level-yok); priced-out kesin-hükmü parse'a bağlı.
- DISC-10: ex-ante-sabit iş-günü pencereler, ex-post-seçim-yok, look-ahead-safe. HÜKÜM/fork yok — maintainer'a.

Kaynaklar (repo-içi, read-only): `scripts/probe/rr_y1_024_b_ma_descriptive_peek.py` (betimsel-only,
strateji-P&L-yok, DISC-10-guarded) · `scripts/probe/kap_bycriteria_client.py` (RR-Y1-025 rota) ·
`data/clean_universe/adjusted_prices_2019_2026.parquet` + `exposure_d187_xu100.parquet` (fiyat/endeks).
İlişkili: RR-Y1-024 (M&A feasibility+collision — bu §3'ünü doldurur), RR-Y1-025 (byCriteria erişim),
RR-Y1-011-E/index_recon (priced-at-announcement dersi — t1-no-jump onu yankılar). Ham ODA-pull commit-edilmedi.
