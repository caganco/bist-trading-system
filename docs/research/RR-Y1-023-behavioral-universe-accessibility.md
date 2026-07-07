# RR-Y1-023 — Davranışsal-evren × enstrüman-erişilebilirlik kesişimi (F1 killer-prob)

**Sınıf:** Enstrüman-erişilebilirlik / evren-kesişim probu. **Stage-0-DEĞİL**, ölçüm-DEĞİL,
edge-iddiası-DEĞİL, hipotez-testi-DEĞİL. Hiçbir strateji koşulmadı; hiçbir getiri / alfa /
holding / forward / event-return / CAR hesaplanmadı. Yalnız **iki olgu** ölçüldü: (a) isim-evreni
karakteristikleri (likidite / oynaklık / lottery-proxy / endeks-üyeliği) ve (b) her isim için
**enstrüman-erişilebilirlik bayrakları**. **Go/no-go kararı bu rapora ait değildir** — maintainer'a aittir.

**Neyi sınar (F1):** Davranışsal-alfanın-yaşadığı-yer (spekülatif / yüksek-oynaklık / illikit /
yüksek-retail-float) ile BIST'te **negatif-görüşün ifade-edilebildiği-yer** (açığa-satış-izinli,
tek-hisse-futures) **ters-örtüşür mü?** Forward-zaman/sermaye harcamadan yönün-değerinin-çoğunu bugün belirler.

---

## §0 — Feasibility (DISC-12: ölçüldü, varsayılmadı)

| Kaynak | Var/Yok | Tarih-aralığı | Çözünürlük | Erişim | Not |
|---|---|---|---|---|---|
| **Açığa-satış izinli/aktif liste** | **VAR** | 2009-01 → 2026-05 (210 aylık dosya) | aylık, per-pay | public DataStore ürünü (offline kanonik arşiv) | `PP_ACIGASATIS` / `acigasat` bültenleri; per-pay işlem-hacmi(TL)/miktar. İzinli-olduğunda ~50 isim listede, **yasakta 0**. |
| **SSF (tek-hisse VİOP futures) dayanak listesi** | **VAR** | 2017-03 → 2026-05 (yoğun 2019+) | aylık, per-kontrat | public DataStore 3208 (offline kanonik) | `VIOP_GUNSONU_FIYATHACIM` ana-seri, segment `SSF`/`D_EQ_FPD`; **50 distinct dayanak** (son-24-ay). (RR-Y1-017 ile tutarlı.) |
| **Varant ihraççı/dayanak listesi** | **VAR** (§5'te ölçüldü) | 1988-01 → 2026-05 | aylık (günsonu-bültenden), per-seri | public DataStore ürünü (offline kanonik) | İlk-sürümde "offline-yok" sanılmıştı; tam günsonu-bülteni `PP_GUNSONUFIYATHACIM` **tüm-piyasayı** kapsar — `ECW`=alım-varantı / `EPW`=**satım(put)-varantı**. §5'te ölçüldü. |
| **Pay-bazında ödünç-pay (SLB/ÖPP) bakiyesi** | **OFFLINE-YOK** | — | — | — | Repoda per-pay borrow-bakiyesi yok. Açığa-satış **işlem-hacmi** birleşik (short+borrow) alt-sınır proxy'sidir (bir pay shortlandıysa borrow vardı). |
| **Evren / likidite / PIT endeks-üyeliği** | **VAR** | 2019-01 → 2026-05 (1848 gün) | günlük, 681 sembol | proje temiz-paneli (D-202) | `adjusted_prices_2019_2026.parquet`: `value_tl` (ADV), `adjusted_close`, PIT `bist30`/`bist100`. |

**Açığa-satış rejim-zaman-serisi (olgu, listede-aktif-isim-sayısı/ay):** izinli rejimde liste
≈ 50 büyük-cap isimle sabittir (= açığa-satış-izinli-pay listesi); yasakta 0'a düşer. Yasak
**aralıklıdır**: 2023-03 → 2024-12 tam-kapalı, 2025-04..08 ve 2026-03..05 yeniden-kapalı,
aradaki aylarda ~50 isim açık. Yani izinli-isimler için bile short-erişimi **kesintilidir**.

---

## §1 — Evren-A (spekülatif / davranışsal-zengin) — donar proxy-tanımı

Snapshot: panel-sonu **2026-05-26**, trailing-pencereler dondurularak. Kriterler (OR):

| Kriter | Operasyonelleştirme | Durum |
|---|---|---|
| Yüksek-oynaklık | trailing-252g yıllıklandırılmış realized-vol, **üst-tercil** | ✅ ölçüldü |
| Yüksek-MAX-getiri | trailing-21g max günlük log-getiri, **üst-tercil** (Bali 2011 lottery-proxy) | ✅ ölçüldü |
| Düşük-piyasa-değeri | ADV **alt-tercil** (küçük-cap proxy) | ✅ ölçüldü (proxy) |
| Gerçek piyasa-değeri | shares-outstanding | **PROXY-YOK** (temiz-panelde yok) |
| Yüksek-retail-float | sahiplik/halka-açıklık verisi | **PROXY-YOK** (panelde yok) |

- **A_broad** (yüksek-vol VEYA yüksek-MAX VEYA düşük-ADV, **bist100-dışı**): **n=355**, medyan-ADV **1.58M TL**.
- **A_core** (yüksek-vol VE yüksek-MAX, bist100-dışı): **n=80**, medyan-ADV **2.65M TL**.

## §2 — Evren-B (olay × likit-büyük-cap)

- **B = PIT BIST-30 üyeleri** (panel-sonu): **n=30**, medyan-ADV **31.8M TL** (≈ A'nın 20×'i).

---

## §3 — Yapısal kontrol (measurement-verification disiplini)

Sonuç (A=%0 vs B=%100) keskin olduğundan, A-tanımının (bist100-dışı) **mekanik olarak** %0
üretip-üretmediği test edildi:

- **Negatif-görüş erişilebilirliği endeksin SIKI alt-kümesidir.** 58 açığa-satış-izinli isimden
  panele-düşenlerin **56'sı bist100, 0'ı endeks-dışı**. 50 SSF dayanağından **48'i bist100, 0'ı
  endeks-dışı** (`neg_eligibility_outside_bist100 = []`). → A'nın endeks-dışı tanımı suni-değil;
   "negatif-enstrümanlar yalnız endeks-üyeleri için var" olgusunun operasyonel karşılığıdır.
- **Endeks-filtresiz** üst-vol tercili (n=198): yalnız **6 isim açığa-satış-izinli, 3'ünde SSF** —
  ve bu 6'sı (BRSAN/DSTKF/KONTR/KUYAS/PASEU/TRALT) **hepsi bist100** büyük/orta-cap'tir. Spekülatif
  mikro-cap havuzunun negatif-erişimi endeks-filtresinden bağımsız olarak da **sıfırdır**.
- **Parser positive-control (kaydedildi):** açığa-satış xlsx formatı 2023+ değişti (`PAY KODU` →
  `İşlem Kodu / Instrument Series Code`, ticker `AKBNK.E` son-ekli). İlk parser sessizce **0 üretti**
  (false-zero); pre-yasak aylarda ~50 isim beklenirken 0 görülmesiyle yakalandı ve düzeltildi.
  Düzeltilmiş parser pre-yasak aylarda ~50, yasak-aylarında 0 verir (beklenen davranış).

---

## §4 — İki-yönlü tablo (her-sayı yukarıdaki kaynaklardan; getiri-yok)

| Metrik | **Evren-A_broad** (spekülatif, n=355) | **Evren-A_core** (lottery, n=80) | **Evren-B** (likit-büyük-cap, n=30) |
|---|---|---|---|
| Negatif-ifade-% (isim-ağırlıklı) | **0.0** | **0.0** | **100.0** |
| Negatif-ifade-% (ADV-ağırlıklı) | **0.0** | **0.0** | **100.0** |
| — açığa-satız-izinli-% | 0.0 | 0.0 | 100.0 |
| — SSF-kapsama-% | 0.0 | 0.0 | 96.7 |
| — likit-put-varant-% (isim / ADV) | 0.0 / 0.0 | 0.0 / 0.0 | 93.3 / 98.9 |
| Borrow-kapsama-% | ölçülmedi (SLB offline-yok; short-hacmi birleşik-proxy) | ölçülmedi | (short-izniyle eşdeğer) |
| Medyan-ADV (TL) | 1.58M | 2.65M | 31.8M |
| Long-ifade-% @ 5M TL | 28.5 | 38.8 | 83.3 |
| Long-ifade-% @ 25M TL | 7.9 | 11.2 | 60.0 |
| Long-ifade-% @ 100M TL | 2.5 | 1.2 | 23.3 |

**Likidite-eşik duyarlılığı (band):** long-ifade-% eşik 5M→25M→100M TL boyunca Evren-A'da
28.5→7.9→2.5 (broad) ve 38.8→11.2→1.2 (core); Evren-B'de 83.3→60.0→23.3. Spekülatif havuzda
anlamlı-pozisyon long-tarafta dahi kapasite-sınırlıdır; negatif-tarafta tümüyle yoktur.

---

## §5 — Varant negatif-view rotası (kapanış-probe'u)

RR-Y1-023'ün tek açık-kalan negatif-view rotası: **varant** (short-izni/SSF gerektirmez).
Bu, tam günsonu-bülteninden (`PP_GUNSONUFIYATHACIM`, offline kanonik) **ölçüldü** —
canlı-fetch/credential gerekmedi (DISC-13). Snapshot: en-güncel aylık bülten (2026-05).

- **Put-varant VAR.** Tek-hisse satım-varantı (`EPW` grubu) **30 distinct dayanak** için
  ihraçta; 29'u likit (≥1M TL/ay; yalnız VAKBN-put ölü-kotasyon <1M). Tek-hisse alım-varantı
  (`ECW`) da aynı 30 dayanak. Endeks/emtia/FX varantları (XAU/BRENT/XU030/DAX/NASDAQ…) ayrı
  işaretlendi, tek-hisse-evreninden hariç tutuldu.
- **Put-varant dayanakları endeksin SIKI alt-kümesi.** 30 dayanağın **30'u bist100, 29'u
  bist30, 0'ı endeks-dışı** — short-izinli + SSF listeleriyle aynı büyük-cap kümesi.
- **Kesişim:** likit-put-varant-kapsama (eşik ≥1M TL/ay) = **Evren-A_broad 0.0% / A_core 0.0%
  (isim ve ADV)**; **Evren-B 93.3% isim / 98.9% ADV** (≥10M TL/ay eşiğinde B 80.0% / 97.6%).
- Endeks-filtresiz üst-vol tercilinde (n=198) likit-put-varantı olan tek-isim = TRALT (o da bist100).

**Sonuç (olgu):** varant rotası F1-hükmünü **değiştirmez** — negatif-görüş varant-yoluyla da
yalnız ~30 büyük-cap endeks-isminde ifade-edilebilir; spekülatif havuzda **%0**. Negatif-view'in
üç rotası da (açığa-satış, SSF, put-varant) aynı büyük-cap alt-kümesine kilitlidir.

---

## NET CÜMLE (öneri-içermeyen)

- **Evren-A (spekülatif) negatif-ifade-% = 0.0** (isim- ve ADV-ağırlıklı; açığa-satış 0.0, SSF 0.0,
  **likit-put-varant 0.0**).
- **Evren-B (likit-büyük-cap) negatif-ifade-% = 100.0** (açığa-satış 100.0, SSF 96.7, put-varant 93.3).
- Negatif-görüşün **üç rotası da** (açığa-satış-izinli liste + SSF dayanakları + put-varant dayanakları)
  **BIST-100'ün sıkı alt-kümesidir**; davranışsal-alfanın yaşayacağı endeks-dışı spekülatif havuzu
  **sıfır** kapsar (F1 ters-örtüşmesi yapısal ve sağlam). İzinli-isimler için bile açığa-satış
  **aralıklı-yasaklıdır** (son ~40 ayın 24'ünde kapalı).

---

## Caveat'lar
- **Yalnız enstrüman-erişilebilirlik + evren-karakteristiği** — getiri/sinyal/edge/CAR ölçülmedi
  (kapsam-dışı, tasarım gereği). Realized-vol & MAX-getiri **evren-tanımlayıcı** sıralama
  değişkenidir, strateji-P&L'i değildir.
- Açığa-satış bülteni **gerçekleşen** short işlem-hacmidir; izin-listesi ile birebir aynı olmayabilir
  (izinli-ama-işlemsiz isim teorik olarak listede görünmeyebilir) → açığa-satış-izinli-% bu yönde
  **alt-sınır** olabilir, ama 58-isim havuzu hepsi-bist100 olduğundan F1-sonucu bu belirsizliğe duyarsızdır.
- Varant **§5'te ölçüldü** (günsonu-bültenden, offline kanonik). Per-pay SLB/ÖPP hâlâ **offline-yok**
  → ölçülmedi, varsayılmadı (short-hacmi birleşik proxy). Varant-dayanak eşleme isim-prefiks-eşleşmesiyle
  (≥4-harf ticker + yapısal-sonek/rakam) yapıldı; endeks/emtia/FX varantları hariç tutuldu.
- KOZAA/KOZAL açığa-satış/SSF listelerinde ama temiz-panelde yok (survivorship/veri-kapsamı); endeks-içi
  sınıflandırmada panele-düşenler kullanıldı.
- Go/no-go **maintainer kararıdır**; bu rapor olgu-sağlar, hüküm-vermez. Fork seçenekleri (kanal-daralt /
  ölçülmemiş-edge-testine-geç / FOLD) bu raporun dışındadır.

Kaynaklar (repo-içi, read-only): `data/bist_datastore_archive/short_selling/` (PP_ACIGASATIS) ·
`data/bist_datastore_archive/viop/` (VIOP_GUNSONU_FIYATHACIM, segment SSF) ·
`data/bist_datastore_archive/prices_official/` (PP_GUNSONUFIYATHACIM, ECW/EPW varant grupları) ·
`data/clean_universe/adjusted_prices_2019_2026.parquet` (D-202) ·
prob-script `scripts/probe/rr_y1_023_behavioral_universe_accessibility.py` (sayım/bayrak-only, getiri-yok, DEC-053-safe).
Dış-bağlam: Bali-Cakici-Whitelaw 2011 (MAX/lottery); Coval-Stafford 2007 (forced flow); RR-Y1-017 (SSF veri-fizibilite).
