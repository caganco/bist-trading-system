# Ghost decision identifiers

Decision identifiers that are **referenced** from code, tests, or research records but have no
record behind them: no file in [`../decisions/`](../decisions/) and no entry in
[`../DECISIONS.md`](../DECISIONS.md). A reader who follows one of these references finds nothing.

This is an inventory, not a repair. Nothing here is reconstructed or guessed: each row lists only
where the identifier is actually cited. Writing the missing records is separate work, and some of
these may turn out to have been informal — in which case the honest outcome is to retire the
identifier, not to author a record after the fact from a guess about what it meant.

**13 ghost identifiers**, against 23 that resolve. Two of them carry real
weight: `DEC-039` and `DEC-053` are cited across dozens of files, so a reader repeatedly meets a
reference that leads nowhere.

| Identifier | Citations | Referenced in |
|---|---|---|
| DEC-039 | 49 | `docs/CODEBASE_INVENTORY_v2.md` · `docs/DECISIONS.md` · `docs/RESEARCH_REGISTRY.md` · `docs/YOL2_REUSABLE_MAP.md` · `docs/event_test/STAGE0_event_confluence_preregistration.json` · `docs/factor_ic/STAGE0_d182_preregistration.json` · …and 43 more |
| DEC-053 | 30 | `data/registry/cross_references.json` · `data/registry/graveyard_registry.json` · `data/verification/pead_verification_results.json` · `docs/RESEARCH_REGISTRY.md` · `docs/research/RR-Y1-016-C-x1-descriptive-asymmetry.md` · `docs/research/RR-Y1-016-CONJUGATE-SPLIT-FREEZE.json` · …and 24 more |
| DEC-045 | 11 | `docs/DECISIONS.md` · `docs/RESEARCH_REGISTRY.md` · `docs/exposure_test/STAGE0_exposure_regime_preregistration.json` · `docs/research/D-187-exposure-rapor.md` · `docs/research/RR-Y1-005-TEST-MOTORU-TASARIM-v-0-2.md` · `docs/research/RR-Y1-005-TEST-MOTORU-TASARIM.md` · …and 5 more |
| DEC-044 | 8 | `CHANGELOG.md` · `docs/DECISIONS.md` · `docs/research/D-186-trend-duzeltme-rapor.md` · `docs/trend_test/STAGE0_d186_preregistration.json` · `src/screening/trend_d186.py` · `src/screening/trend_d186_config.py` · …and 2 more |
| DEC-049 | 6 | `docs/RESEARCH_REGISTRY.md` · `docs/engine/OPERATOR_GUIDE.md` · `docs/research/RR-Y1-009-VERDICT-CONFIDENCE-LOCKBOX.md` · `src/engine/confidence.py` · `src/engine/config.py` · `src/engine/contracts.py` |
| DEC-014 | 5 | `docs/RESEARCH_REGISTRY.md` · `docs/research/RR-032-V3-OPENSOURCE-VE-SMART-MONEY.md` · `docs/research/RR-037-smartmoney-veri-erisim.md` · `src/analytics/brinson_attribution.py` · `src/signals/layers/viop_layer.py` |
| DEC-054 | 4 | `data/registry/graveyard_registry.json` · `docs/RESEARCH_REGISTRY.md` · `docs/yol1/CONSISTENCY_AUDIT.md` · `docs/yol1/LOCALIZATION_REPORT.md` |
| DEC-064 | 4 | `docs/RESEARCH_REGISTRY.md` · `docs/research/RR-Y1-027-frictionless-layer.md` · `src/engine/frictionless.py` · `tests/test_engine_frictionless.py` |
| DEC-035 | 3 | `docs/DECISIONS.md` · `docs/yol1/CONSISTENCY_AUDIT.md` · `docs/yol1/LOCALIZATION_REPORT.md` |
| DEC-018 | 1 | `docs/specs/SPEC_IC_FRAMEWORK_1.md` |
| DEC-024 | 1 | `docs/features/IC_FRAMEWORK.md` |
| DEC-025 | 1 | `docs/features/RISK_LAYER.md` |
| DEC-055 | 1 | `scripts/verification/verify_pead_stage0.py` |

## How to close a row

Either write the record the reference should have pointed to and update the citing lines to the
new `ADR-NNNN`, or, if no decision was ever actually taken under that identifier, remove the
citation. Do not back-fill a record from a guess.
