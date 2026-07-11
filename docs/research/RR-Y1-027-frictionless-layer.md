# RR-Y1-027 — İdeal / frictionless ölçüm-katmanı (DEC-064) + sentetik IPO golden-vakası

**Sınıf:** doğrulama-altyapısı (validation infrastructure; DEC-064 implementasyonu).
**Stage-0-DEĞİL**, ölçüm-DEĞİL, herhangi bir gerçek araştırma-adayı üzerinde **hüküm-DEĞİL**;
hiçbir getiri ölçülmedi, hiçbir frozen-pencere/X₂ tüketilmedi. Yeni, **eklenti (additive)** bir
modül — committed Mod-A/B/C motoru, `src/engine/multiple_testing.py` ve mevcut hiçbir test
değiştirilmedi (strangler). Yalnız **sentetik fixture** ile doğrulanır.

**Ne çözer:** Her Stage-0 koşusu artık **tek** nedensel-pipeline'dan **iki rapora** ayrılabilir:
*gerçekçi* (tam-sürtünme → HÜKÜM) ve *ideal/frictionless* (para-sürtünmesi-sıfır →
KONSEPT-LEDGER, **asla hüküm-vermez**). Bu, "olgu var ama trade-edilemez" durumunu — bir
**sürtünme-mezarı**nı (friction-grave) — olgu-mezarından (graveyard) ayırt etmeyi *mümkün-kılar*,
ama kararı **vermez**.

Modül: `src/engine/frictionless.py`. Testler: `tests/test_engine_frictionless.py`.

---

## §3 — Yük-taşıyan ayrım (bu satır bulanırsa katman "hile" olur)

İki kuvvet-sınıfı **kesin** ayrılır:

| Sınıf | İdeal-katmanda | İçerik |
|---|---|---|
| **PARA-SÜRTÜNMESİ** | **SIFIRLANIR** | komisyon, slippage, spread, execution-timing **VE** fill-erişilebilirliği/tradability (tahsis-kura, tavan-kilit, likidite-derinliği) |
| **NEDENSELLİK-FİZİĞİ** | **KORUNUR** | look-ahead-safe (gelecek-sızıntısı-yok), survivorship (silinen/iflas-eden enstrüman diriltilmez), t→t+1 zaman-oku |

İdeal-katman *frictionless-fill* alır — referans-fiyattan dolduğunu varsayar; **gelecek-peek
ALMAZ.** Pozisyon-serisi (sinyal→ağırlık→forward-toplam-getiri) **bir kez**, yukarı-akışta,
look-ahead-safe kurulur (next-open / önceden-tanımlı pencere; ex-post-zirve-seçimi YASAK, DISC-10).
İki katman **yalnız maliyet-uygulama-aşamasında** ayrışır.

Mekanik (tek-kural, iki-katman ortak):

```
net = gross × fill_fraction − cost_ann − tax_ann − access_haircut_ann
```

`fill_fraction` aktif-maruziyeti ölçekler (kısmi-fill → kısmi-tilt); diğerleri getiri-drag'ı.
`FrictionParams.null()` (hepsi-sıfır, tam-fill) ile bu **özdeşliktir**: `net == gross`.

---

## §4 — Doğruluk-özelliği (katmanın kendi ölçüm-doğrulama çıpası)

İki katman aynı pozisyon-serisini paylaşıp yalnız maliyet-uygulamada ayrıştığı için,
**gerçekçi-katman tüm maliyet-parametreleri sıfıra çekilince ideal-katmanı BİT-BİT
yeniden-üretmelidir:**

```
apply_friction(gross, FrictionParams.null()) == gross == ideal.net_active_ann
```

`DualLayerReport.differential_invariant_holds()` tam bunu doğrular; golden-fixture dondurur.
Paylaşılan pozisyon-serisi `position_fingerprint` (sha256[:16]) ile auditable — iki katmanın
gerçekten **aynı** nedensel-pipeline'ı tükettiği denetlenebilir.

---

## §5 — Çıktı-kontratı

- **gerçekçi → HÜKÜM** (`is_verdict=True`, etiket `REALISTIC / VERDICT`); tam-maliyet; mevcut
  verdict-yolu, **değişmez**.
- **ideal → KONSEPT-LEDGER, HÜKÜM-VERMEZ** (`is_verdict=False`, etiket
  `IDEAL — NON-VERDICT / CONCEPT-LEDGER`). Etiket **hem insan-okur başlıkta hem makine-okur
  sözlükte** (`NON_VERDICT=True`, `concept_ledger=True`) taşınır — sayı asla
  promosyon/deploy-gerekçesi yapılamaz.
- **Statü-merdiveni kancası (`friction_grave_hint`):** güçlü-ideal **VE** ölü-gerçekçi **VE**
  ayrışma fill/tradability-kaynaklı (yalnız para-maliyeti değil) → **sürtünme-mezarı ADAYI**
  (save/wait + konsept-ledger, olgu-mezarından AYRI). Ayrışma salt-para-maliyetiyse → düz
  *cost-fail*, sürtünme-mezarı-DEĞİL. Kanca **her zaman `requires_human=True`** döndürür —
  sınıflama maintainer/Orchestrator hükmüdür; katman OTOMATİK-KARAR-VERMEZ.

**Additivite (kanıt):** `from_engine_output()` committed `EngineOutput`'u salt-okur — ideal-katman
motorun **gross**'unu (`gross_active_ann`), gerçekçi-katman motorun **net**'ini
(`gross − cost − tax`) **değiştirmeden** geri-verir. Verdict-katmanı sayıları **kıpırdamaz**
(`TestAdditivityVsHarness`).

---

## §6 — Sentetik IPO golden-vakası (NON-VERDICT / SYNTHETIC-CALIBRATION)

**Bu bir IPO-bulgusu DEĞİLDİR.** S#21-peek'in n=24 IPO paneli hiçbir clone/ana-repoda
committed-değil ve `clean_universe`'de listing-date yok → "yeniden-toplama-yok" kısıtını ihlal
etmeden diskten rekonstrüksiyon mümkün-değil. Maintainer revize-§6 kararı gereği yetenek
**mekanik olarak** sentetik deterministik golden-fixture ile doğrulanır (MTH SIZE/POWER
golden'ının muadili); **gerçek-veri n=24 validation ERTELENİR** (aşağıda + RESEARCH_REGISTRY).

**Ön-kayıtlı senaryo (sayı-okunmadan donmuş):** ideal-katman ilk-hafta-pop olgusunu gösterir
(gross > 0, sentetik `0.40`); gerçekçi-katman IPO tradability-duvarıyla (tahsis-kura
`fill=0.10` + secondary tavan-kilit `access_haircut=0.04`, `cost=0.015`) **net ≈ 0/negatif**'e
öldürür (`−0.015`). Bu sapma = sürtünme-mezarı kavramının somut-kanıtı. Çıktı pure-arithmetic →
**byte-stable** (sürüm/kütüphane-bağımsız), iki-kez bit-aynı.

| Katman | gross | net | hüküm |
|---|---|---|---|
| gerçekçi | 0.40 | **−0.015** | VERDICT (ölü) |
| ideal | 0.40 | **0.40** | NON-VERDICT (olgu görünür) |

`friction_grave_hint`: `candidate=True`, `tradability_bound=True`, `requires_human=True`.

**ERTELENEN — gerçek-veri n=24 IPO validation:** gerçek-panel committed-olmadığından ertelenir.
Re-collection ayrı bir açık-veri-task'ıdır (DISC-1: yüksek-önselli-canlı-aday-yok; düşük-değer:
olgu zaten konsept-ledger-sınıflı, confirmatory). **Upgrade-path:** S#21 n=24 paneli kayıtlı-dosya
olarak sağlanırsa aynı iki-katman + §4 + §7 mekaniği gerçek-panele uygulanır, frozen-fixture
gerçek-veriyle dondurulur, §6/§8 orijinal-haliyle tam-karşılanır (re-collection yine yapılmaz).

---

## §7 — Ölçüm-doğrulaması (measurement-verification; differential + metamorphic + placebo)

Katman hüküm-vermez ama zaman-oku/survivorship bug-taşıyabilir → protokol **zorunlu** koşuldu.
Tüm kontroller fixture-öncesi donduruldu (tuning-yok). Sonuçlar `tests/test_engine_frictionless.py`.

**Faz-0 (doğru-ne-olurdu):** iddia = "iki katman aynı pozisyon-serisinden, yalnız maliyet-aşamasında
ayrışır; ideal-katman gelecek-peek değil frictionless-fill alır". Tehlikeli-hata = ideal-katmanın
zaman-okunu (sessizce) gevşetip sahte-pozitif fabrikası olması (false-PASS sızıntı-yönü).

| Faz | Kontrol | Beklenen | Gözlenen |
|---|---|---|---|
| **1 — Differential** | gerçekçi(maliyet=null) == ideal, bit-bit | `==` | PASS (`test_realistic_at_null_reproduces_ideal_bit_for_bit`, `differential_invariant_holds`) |
| **1 — Additivite** | katman motorun gross/net'ini değiştirmeden verir | `==` | PASS (`TestAdditivityVsHarness`; gerçek harness'la) |
| **2 — Metamorphic** | cost↑/access↑/fill↓ → net **monoton-bozulur**; null sınırında ideal'e yakınsar | monoton | PASS (`TestMetamorphic`, 4 kontrol) |
| **3 — Placebo** | sinyal↔getiri shuffle → kenar çöker (ideal-dahil); ideal noise'tan sinyal üretemez | ≈0 | PASS (`test_placebo_collapses_relative_to_the_real_edge`) |
| **3 — Look-ahead injection** | pozisyon realized-return'ü peek-ederse → ideal-katman **şişer** (zaman-oku gerçekten-mekanikte-korunuyor) | leak ≫ safe (×3+) | PASS (`test_look_ahead_injection_inflates_the_ideal_layer`) |

**Look-ahead-injection yorumu (yük-taşıyan):** ideal-katmanı koruyan şey **zaman-oku**dur,
sürtünme-knob'u değil — zaman-okunu kasıtlı kırınca ideal-katman balonlaşır (leak/safe > ×3).
Bu, korumanın salt-isimde değil **mekanikte** olduğunu kanıtlar.

**İnsan-checkpoint (protokol-zorunlu):** sentetik golden-vaka kanonik-kabul-edilmeden önce bir
insan tarafından somut-okuma ile teyit edilir — bu doküman §6 tablosu (gerçekçi −0.015 / ideal
0.40 / candidate=True) maintainer onayına sunulur; PR DO-NOT-MERGE bu checkpoint'i temsil eder.

**Faz-5 hüküm (ölçüm-güvenilirliği):** **TRUSTWORTHY** — differential birebir, metamorphic
ilişkiler tutuyor, placebo null, look-ahead-injection beklendiği gibi şişiriyor. Doğrulanamayan:
gerçek-veri n=24 IPO vakası (ERTELENDİ — sentetik-kalibrasyon mekanizmayı doğrular, gerçek-büyüklüğü
değil; bu dürüstçe beyan-edilir).

---

## §8 — Tamamlanma-kapısı (durum)

- ✅ Mevcut suite yeşil (**2122 passed / 5 skipped / 0 fail**, ölçülen taban) + yeni 23 test.
- ✅ MTH-golden + architecture + harness byte-aynı (90 passed / 1 skipped; verdict-sayıları değişmedi).
- ✅ Yeni-modül additive; Mod-A/B/C + `multiple_testing.py` committed-koduna **düzenleme-yok**.
- ✅ §4 differential-invariant determinist tutuyor.
- ✅ IPO-validation ön-kayıtlı iki-katman-sapmasını üretiyor (sentetik); byte-stable.
- ✅ measurement-verification raporu ekli (differential + metamorphic + placebo + insan-checkpoint).
- ✅ RESEARCH_REGISTRY satırı (RR-Y1-027), ID-sırasında.
- 🟡 **DEFERRED:** gerçek-veri n=24 IPO validation (panel-committed-değil; RESEARCH_REGISTRY'de işaretli).

---

## Caveat'lar

- **Bu modül hiçbir gerçek BIST adayını değerlendirmez** — yalnız sentetik fixture kalibrasyonu.
  Bir gerçek aday üzerinde kullanımı + sürtünme-mezarı sınıflaması ayrı, soğuk bir maintainer
  kararıdır (katman yalnız mümkün-kılar).
- **İdeal-katman sayısı asla bir hüküm değildir** (F-NON-VERDICT) — etiketi hem başlıkta hem
  makine-sözlüğünde taşınır; konsept-ledger olarak loglanır, deploy-gerekçesi olamaz.
- **Sentetik golden gerçek-büyüklüğü kanıtlamaz** — mekaniği (differential/metamorphic/placebo/
  zaman-oku) kanıtlar; gerçek-veri-validation upgrade-path'e bağlı.
- **fill/access modeli mevcut harness maliyet-modelinde (Roll+Kyle) yoktur** — IPO tahsis-kura/
  tavan-kilit gibi tradability-sürtünmeleri çağıran tarafından `tradability` overlay olarak
  verilir; bu bilinçli (harness cost-modeli para-maliyetini kapsar, fill-erişilebilirliğini değil).

Kaynaklar: DEC-064 (iki-rapor mandate) · RR-Y1-005 (Mod-A/B/C doğrulama-motoru — strangler
eklenti) · RR-Y1-022 (MTH golden-fixture precedent) · DISC-10 (ex-ante pencere, look-ahead-safe) ·
measurement-verification protokolü (differential/metamorphic/placebo).
