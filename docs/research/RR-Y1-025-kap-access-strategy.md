# RR-Y1-025 — KAP erişim-stratejisi: ortak veri-darboğazının tek-seferlik çözümü

**Sınıf:** Veri-erişim / altyapı araştırma probu. **Stage-0-DEĞİL**, ölçüm-DEĞİL, edge-iddiası-DEĞİL;
hiçbir getiri/CAR hesaplanmadı. Yalnız **KAP erişim-rotası teşhisi + çalışan-rotanın doğrulanması +
üç olay-adayının veri-zenginliği ölçümü**. DISC-13: yalnız public no-auth; credential/WAF-bypass yok
(sitenin kendi warm-up cookie'si dışında). **Go/no-go + tam-backfill kararı maintainer'a.**

**Motivasyon:** Üç olay-adayı da (M&A/zorunlu-teklif · pay-geri-alım/buyback · insider/yönetici-işlem,
ve FDP'nin fon-tarafı) KAP **ÖDA** (Özel Durum Açıklaması) PIT-akışına bağlı. KAP erişimi tek-seferlik
çözülürse üçü de açılır. RR-Y1-024 (M&A) ve RR-Y1-021 (FDP) "KAP WAF-gated" duvarına çarpmıştı — bu
rapor o duvarın **yanlış endpoint** olduğunu gösterir ve çalışan rotayı kurar.

---

## §1 — Rota teşhisi (ölçüldü, 2026-06-15, bu ağ)

| Endpoint | Sonuç | Not |
|---|---|---|
| `POST /tr/api/memberDisclosureQuery` | **WAF-TARPIT** | Bağlantı kabul edilir, yanıt kara-deliğe düşer: **6/6 deneme × 25s timeout**, warm-up cookie'yle bile. Legacy `src/data/kap_scraper.py` + RR-Y1-024'ün ilk-probları bu endpoint'i kullandığı için "often WAF-blocked" raporladı. |
| `GET /tr/bildirim-sorgu` | **200** | `KAP` + NetScaler WAF cookie'leri (`NSC_*.lbq.psh.us`, `AGVY-Cookie`) verir — warm-up için gerekli. |
| `POST /tr/api/disclosure/members/byCriteria` | **200, ~0.3s** | **ÇALIŞAN ROTA.** No-auth; yalnız warm-up cookie. Tam-kayıt döner: `publishDate` (PIT), `stockCodes`, `relatedStocks`, `subject` (konu), `summary`, `disclosureClass`, `disclosureIndex` (stabil-id), `attachmentCount`. (index-recon işinin cache'lediği rota — kanıt: `kap_index_probe/recon_cache/`.) |
| `GET /tr/api/.../subjects` (konu-taksonomisi) | **404** (5 varyant) | subjectList-OID server-filtresi yok → `subject` **metin**iyle post-filtre. |

**Teşhis:** KAP duvarı **genel-değil, endpoint-spesifik**. `memberDisclosureQuery` tarpit'li;
`byCriteria` serbest. Credentialed MKK VYK API (token) gereksiz — public byCriteria yeterli.

---

## §2 — Çalışan reçete (reusable client)

`scripts/probe/kap_bycriteria_client.py`:

1. **Warm-up:** `GET /tr/bildirim-sorgu` → `KAP` + WAF cookie.
2. **Sorgu:** `POST byCriteria` (`disclosureClass=ODA`, tarih-aralığı, member-filtresiz = tüm-şirketler).
3. **2000-kayıt cap:** tek sorgu **≤2000** döner; yarım-ay bile cap'e çarpar (2026-05-01..15 = 2000).
   → **adaptive date-bisection** (pencereyi <2000 olana dek ikiye böl) + `disclosureIndex` dedupe.
4. **Konu-filtresi (post-filter, `subject` metni):** buyback = "Payların Geri Alınmasına İlişkin Bildirim";
   insider = "Pay Alım Satım Bildirimi"; tender/M&A = "Pay Alım Teklifi" / "Birleşme" / "Devralma" /
   "Ortaklıktan Çıkarma".
5. **PIT:** `publishDate` = anons-zaman-damgası (look-ahead-safe entry = publishDate+1-seans).
6. **Fiyat (teklif/buyback/çıkarma bedeli):** top-level alan **değil** → `attachmentCount>0` ek-form
   (per-disclosure detail fetch + şablon-parse) gerektirir — **ayrı mühendislik, bu raporda yapılmadı**.

---

## §3 — Uçtan-uca doğrulama (2025, gerçek-pull)

byCriteria + bisection ile **2025 = 36.971 ODA bildirimi** çekildi (raw cache git-ignored,
commit-edilmedi). Üç-aday konu-filtresiyle:

| Aday | 2025 bildirim | distinct isim |
|---|---|---|
| **Buyback** (pay geri-alım) | **3.822** | 287 |
| **Insider/yönetici-işlem** | **2.147** | 90 |
| **Tender/M&A/birleşme/çıkarma** | **403** | 94 |

→ Üçü de **veri-zengin ve PIT-capturable**. (M&A ~400/yıl, RR-Y1-024'ün delisting-proxy'sinin çok
üstünde — proxy alt-sınırdı, doğrulandı.) **Tek-yıl 2025 örneği**; tam 2018-2026 backfill aynı
client'la (yılda ~37k×8 ≈ veri-ağır ama ~dakikalar) — maintainer kararı.

---

## §4 — Ne açıldı / ne kaldı

**Açıldı (erişim çözüldü):**
- **Olay-akışı + PIT-tarih + ticker + konu** üç-aday için de (M&A · buyback · insider) byCriteria'dan
  ücretsiz/no-auth çekilebilir; FDP fon-tarafı da aynı ÖDA-akışında.
- RR-Y1-024 "scrapable-ama-WAF-gated" + RR-Y1-021 "KAP-WAF" duvarları **kalktı** (yanlış-endpoint'ti).

**Kalan mühendislik (maintainer kararı — bu rapor yapmadı):**
1. **Tam tarihsel backfill** (2018/2019→2026) + kalıcı owned-arşiv (raw commit-edilmez; insider
   flow_intel emsali gibi yerel-store).
2. **Fiyat-parse:** teklif/buyback/çıkarma bedeli ek-form şablonundan (`attachmentCount>0`) çıkarımı —
   tradability/merger-arb-spread için şart; semi-structured parse.
3. **Konu-OID kesinleştirme:** post-filtre metin-tabanlı (robust ama OID-server-filtresi daha-temiz olurdu;
   taksonomi-GET 404 olduğundan metin-filtre kullanıldı).

---

## NET CÜMLE (öneri-içermeyen)

KAP erişimi **çözüldü**: duvar genel-değildi, `memberDisclosureQuery` endpoint'ine özgü WAF-tarpit'iydi;
**`disclosure/members/byCriteria` (no-auth, warm-up + adaptive-bisection) çalışıyor** ve üç olay-adayının
(M&A 403 · buyback 3.822 · insider 2.147 bildirim/2025) PIT-metadata'sını veriyor. Fiyat-alanı ek-form
parse'ı + tam-backfill ayrı mühendislik olarak kalır.

---

## Caveat'lar
- Yalnız erişim + metadata-zenginlik — getiri/edge/CAR ölçülmedi (tasarım-gereği).
- Rota-teşhisi **bu-ağ/bu-seans** statüsüdür (2026-06-15); WAF kuralları değişebilir. byCriteria 2026-06-09'da
  da çalışmıştı (recon_cache) → en az 6-gün stabil.
- Fiyat top-level değil (ek-form) → tradability tam-feasibilitesi fiyat-parse'a bağlı (henüz yapılmadı).
- Raw pull (2025, 21MB) **commit-edilmedi** (git-ignored archive); yalnız client + bu rapor + sayımlar.
- DISC-13: warm-up cookie sitenin-kendi mekanizması; credential/login/CAPTCHA/token **kullanılmadı**.

Kaynaklar (repo-içi, read-only): `scripts/probe/kap_bycriteria_client.py` (reusable client; metadata-only,
getiri-yok) · `data/bist_datastore_archive/kap_index_probe/recon_cache/` (byCriteria önceki-cache, rota-kanıtı) ·
`src/data/kap_scraper.py` (tarpit-li memberDisclosureQuery legacy) · `scripts/scratch/_fetch_all_disc_ids.py`
(byCriteria quarterly-split emsali). İlişkili: RR-Y1-024 (M&A feasibility — bu rapor sample-count'unu açar),
RR-Y1-021 (KAP-WAF bulgusu — bu rapor düzeltir), RR-Y1-019 (KAP konu-taksonomisi), RR-Y1-016 (insider scrape soyu).
