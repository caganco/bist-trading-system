# RR-Y1-024 — M&A / zorunlu-pay-alım-teklifi / ortaklıktan-çıkarma: feasibility + mezarlık-collision probe

**Sınıf:** Feasibility + graveyard-collision probu. **Stage-0-DEĞİL**, ölçüm-DEĞİL, edge-iddiası-DEĞİL,
hipotez-testi-DEĞİL. Hiçbir strateji koşulmadı; hiçbir getiri/CAR/forward-return hesaplanmadı. Yalnız:
(a) veri-feasibility, (b) mezarlık-collision (C7/C8/C9 + olay-eksenleri), (c) sample-count owned-proxy,
(d) universe×tradability skew. **Fork/go-no-go bu rapora ait değildir** — maintainer'a aittir.
DISC-12: feasibility prob-öncesi-iddia-edilmez. DISC-13: credential kullanılmadı.

Evren-B (olay × likit-büyük-cap) ilk-Tier-1-adayı = M&A / zorunlu-pay-alım-teklifi / ortaklıktan-çıkarma.

---

## §0 — FEASIBILITY (DISC-12: ölçüldü, varsayılmadı)

### Olay-akışı (event date + ticker)
| Boyut | Bulgu |
|---|---|
| KAP konu-taksonomisinde var mı | **VAR** — VBTS'in aksine (RR-Y1-019), pay-alım-teklifi / ortaklıktan-çıkarma / birleşme-devralma KAP **ÖDA** (Özel Durum Açıklaması) konularıdır. Repo scraper'ı anahtar-kelimeleri tanır: `src/data/kap_scraper.py` ("birleşme", "devralma", "m&a", "zorunlu pay alım", "merger", "acquisition"). |
| Düzenleyici çıpa | Zorunlu pay-alım-teklifi = SPK Tebliği **II-26.1** (Pay Alım Teklifi Tebliği); ortaklıktan-çıkarma/satma-hakkı = **II-27.x** (Ortaklıktan Çıkarma ve Satma Hakları); birleşme/bölünme = II-23.x. |
| Owned/PIT arşiv mi | **YOK** — `flow_intel` DB yalnız insider-işlem (RR-Y1-016); `corporate_actions` arşivi **boş** (0 dosya); `kap_fr_*` yalnız finansal-rapor. M&A/teklif olayları **owned-değil**. |
| Credentialed API | MKK VYK API (`src/data/kap_api_client.py`, ÖDA sınıfı) **token gerektirir** → **DISC-13 bloklar.** |
| Public no-auth route | `kap.org.tr/tr/api/memberDisclosureQuery` — bu seansta **2× read-timeout (140s) / WAF-gated** (RR-Y1-021'in KAP WAF-666/500 bulgusuyla tutarlı). `disclosureQuery` → 404. |
| **Sonuç (olay)** | **Prensipte-scrapable (public konu-taksonomisi) ama bu seansta CANLI-ÇEKİLEMEDİ** (WAF/timeout); owned-arşiv yok. Sample-count canlı/scrape rotasına bağlı (insider fresh-scrape soyu gibi ayrı mühendislik) veya credentialed-API (DISC-13 bloklu). |

### Teklif/çıkarma fiyatı (capturable mı — yapısal-alan mı serbest-metin mi)
- Zorunlu-teklif fiyatı + çıkarma-bedeli KAP **"Pay Alım Teklifi Bilgi Formu"** şablonunda yer alır → **yarı-yapısal** (form-template). Serbest-numerik-alan **DEĞİL**: güvenilir çıkarımı şablon-parse eforu gerektirir (capturable-with-parse-effort). Tarih-aralığı/çözünürlük = olay-bazlı (anons-tarihi PIT).

---

## §1 — PROVENANCE / COLLISION (mom120-gate analoğu)

Graveyard'daki **olay/event-eksenleri** ve tanımları (transcribed, registry'den):

| Aday | Eksen | Ne ölçtü (tanım) | Verdict | M&A-collision? |
|---|---|---|---|---|
| **C7** `c7_negative_veto` | event-tilt | **"düşen-bıçak" negatif-seçim VETO**'su (5-koşul, dik-düşüşteki isimleri ele) | measured-NEGATIVE (LIQUID 4/5 near-miss) | **HAYIR** — fiyat-momentum vetosu, kurumsal-olay değil |
| **C8** `c8_core_satellite` | event-tilt | **core-satellite 80/20 re-tilt** (portföy-inşası) | measured-NEGATIVE (4/5; rastgele-tilt'ten ayrışmaz) | **HAYIR** — portföy-konstrüksiyonu, olay değil |
| **C9** `c9_event_sector_tilt` | event-tilt | **şok-sonrası kazanan-SEKTÖR göreli-drift**'i ([T+1,+20], N=9) | measured-NEGATIVE (sign-test 3/9 FAIL) | **HAYIR** — makro/piyasa-şoku sektör-drifti; kurumsal-aksiyon-M&A değil |
| `index_recon_xu030_in` | mechanical-flow | **XU030 periyodik yeniden-yapılanma IN** talep-şoku (CAR, N=24) | SERAP (NW-t 0.052; anons-penceresinde fiyatlanmış) | **HAYIR ama METODOLOJİK-ANALOG** (aşağı bak) |
| `h2b_dividend_runup` | cross-sectional | temettü-öncesi capture-penceresi | KESIN-KAPANDI | HAYIR — temettü-olayı |
| `insider_disclosure_*` | event-tilt | KAP insider buy/sell yön + cluster | TRADEABLE-DEGIL | HAYIR — insider-işlem-olayı |
| `pead` (PENDING) | event-tilt | kazanç-sonrası drift | PENDING | HAYIR — kazanç-olayı |

**COLLISION VERDICT: DIFFERENTIATED.** M&A / zorunlu-pay-alım-teklifi / ortaklıktan-çıkarma **hiçbir
graveyard-adayı tarafından test-edilmedi**; C7 (momentum-veto), C8 (portföy-inşası), C9 (sektör-drift)
ile çakışma **yok** — olay-türü ve mekanizma farklı.

**KRİTİK UYARI-ANALOG (collision-değil ama ders):** `CLOSURE-mechanical-flow` (index_recon). Mantık
birebir-paralel: zorunlu-teklif de **sabit-fiyatlı, fiyat-duyarsız, public-anons-edilmiş mekanik
talep**tir. index_recon dersi = böyle mekanik-talep **public-anons penceresinde fiyatlanır** (arb'lar
pre-pozisyon alır), tam-örneklemde NW-t≈0 + half-split sign-flip. Aynı "merger-arb spread sıfıra-yakınsar"
riski M&A-adayının §3-peek'inin sınaması gereken şeydir (bu seansta veri-duvarında bloklu).

---

## §2 — SAMPLE-COUNT + UNIVERSE × TRADABILITY

**Owned M&A/teklif olay-sayısı: ÖLÇÜLEMEDİ** (yukarıdaki veri-duvarı; fabrike-edilmez, DISC-12).

**Owned delisting / terminal-kurumsal-olay PROXY'si** (`adjusted_prices_2019_2026.parquet`, son-işlem
< panel-sonu−60g):

- **n = 73** terminal-olay-ismi (2019-2026). Yıl-dağılımı: 2019:5 · **2020:25** · 2021:9 · 2022:7 · 2023:3 ·
  2024:10 · 2025:12 · 2026:2 (2020 muhtemelen yapısal delisting-dalgası).
- **Likidite skew'i (tradability-ilgili):** medyan-ADV **0.9M TL** (mikro). ADV≥5M = %20.5; ≥25M = %6.8;
  ≥100M = **%0.0**. Yalnız **12/73** hiç-bist100, **4/73** hiç-bist30 olmuş (ANACM/SODA/TRKCM = Şişecam-grubu
  birleşme/squeeze; KOZAA/KOZAL = halt).
- **PROXY-UYARISI:** bu 73-isim M&A/squeeze'i **iflas/transfer/regülatif-delisting ile karıştırır** →
  M&A-olay-sayısının üst-sınırı, gerçek-sayı değil; ama likidite-skew'i için bilgi-verici. Kontrol-değişikliği
  ile tetiklenip **delisting-etmeyen** zorunlu-teklifler bu proxy'de **yok** (daha-likit isimler içerebilir).

**Tradability okuması (olgu):** terminal-kurumsal-olay evreni ağırlıkla **mikro-cap** (medyan-ADV ~0.9M TL,
%0'ı ≥100M) → F1 deseniyle aynı yönde. M&A-merger-arb tipik olarak **long** (hedefi teklif-fiyatının-altında
al, yakınsamayı yakala) olduğundan F1 negatif-view-duvarı burada **daha-az-bağlayıcı**; bağlayıcı-olan
**long-taraf likiditesi + spread-zaten-kapanmış-mı** (index_recon analoğu).

---

## §3 — BETİMSEL-PEEK (opsiyonel)

**DEFERRED — aynı veri-duvarında bloklu.** Anons-öncesi-yakınsama vs anons-sonrası-spread/drift ölçümü
zorunlu-teklif **olay-tarihleri + teklif-fiyatları**nı gerektirir; ikisi de owned-değil ve KAP canlı-rota
WAF-gated. Hiçbir ex-post zirve/dip-seçimi yapılmadı (DISC-10); pencere-seçimi de yapılmadı. Veri-rotası
açıldığında anons-tarihi-merkezli look-ahead-safe betimsel-dağılım (medyan/IQR) ile koşulabilir.

---

## NET CÜMLE (öneri-içermeyen)

- **Feasibility:** olay-ekseni KAP konu-taksonomisinde **var** (VBTS'in aksine) ve prensipte public-scrapable,
  ama owned-arşiv **yok** + public KAP query bu seansta **WAF/timeout-gated** + credentialed-API DISC-13-bloklu
  → sample-count canlı/scrape mühendisliğine bağlı. Teklif-fiyatı **yarı-yapısal** (form-parse eforu).
- **Collision:** M&A/teklif/squeeze = **DIFFERENTIATED** (C7/C8/C9 ve diğer olay-eksenleriyle çakışma yok);
  tek ilgili **uyarı-analoğu** index_recon (mekanik-talep public-anonsta-fiyatlanır) — collision değil, ders.
- **Sample/tradability:** owned olay-sayısı ölçülemedi; delisting-proxy (n=73, medyan-ADV 0.9M TL, ≥100M %0,
  12/73 ever-bist100) terminal-kurumsal-olay evreninin **mikro-cap-ağırlıklı** olduğunu gösterir.

---

## Caveat'lar
- Yalnız feasibility + collision + owned-proxy — getiri/CAR/edge ölçülmedi (tasarım gereği, kapsam-dışı).
- KAP canlı-erişim **2× denendi, WAF/timeout** — bypass denenmedi (DISC-13); başka seans/route'ta erişilebilir
  olabilir (RR-Y1-016/019 KAP'ı başka rotalarla çekebilmişti). Feasibility "bu-seans" statüsüdür.
- Delisting-proxy M&A-olay-sayısı **değildir** (iflas/transfer/regülatif karışır); üst-sınır + skew-göstergesi.
- Collision transcribe-edilmiştir (registry artefaktları); hiçbir aday yeniden-koşulmadı/yeniden-parametrize-edilmedi.
- Go/no-go + fork (Stage-0-aç / başka-Tier-1-adayına-geç / FOLD) **maintainer kararıdır**.

Kaynaklar (repo-içi, read-only): `data/registry/graveyard_registry.json` (C7/C8/C9 + olay-eksenleri) ·
`data/registry/cross_references.json` (CLOSURE-mechanical-flow analoğu) ·
`src/data/kap_scraper.py` (M&A anahtar-kelimeleri) · `src/data/kap_api_client.py` (MKK VYK, credentialed) ·
`data/clean_universe/adjusted_prices_2019_2026.parquet` (delisting-proxy) ·
prob-script `scripts/probe/rr_y1_024_ma_event_feasibility_proxy.py` (sayım/bayrak-only, getiri-yok, DEC-053-safe).
Dış-çıpa: SPK II-26.1 (pay-alım-teklifi), II-27.x (ortaklıktan-çıkarma); RR-Y1-019 (KAP konu-taksonomisi),
RR-Y1-021 (KAP WAF gating), RR-Y1-011-E / index_recon (mekanik-flow priced-at-announcement dersi).
