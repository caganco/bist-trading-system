# Ghost Decision Inventory — Resolution Status

Decision identifiers referenced across the codebase and research records with no surviving
written record. A reader who follows one of these finds nothing.

**Resolution rule.** Where the decision can be reconstructed from surviving evidence and the way
it was actually applied, it is restated as an ADR and marked resolved. Where it cannot, it is
left *definition unrecoverable* — an honest dangling pointer, never a fabricated record.

**4 of 14 resolved.** The two heaviest are now closed: `DEC-039` and `DEC-053`
together accounted for most of the dangling references in the tree.

| Identifier | Citations | Resolution | Referenced in |
|---|---|---|---|
| DEC-039 | 49 | **Resolved → ADR-0009** — evidence hierarchy + single-pass | `docs/CODEBASE_INVENTORY_v2.md` · `docs/DECISIONS.md` · `docs/RESEARCH_REGISTRY.md` · `docs/YOL2_REUSABLE_MAP.md` · `docs/event_test/STAGE0_event_confluence_preregistration.json` · …and 44 more |
| DEC-053 | 30 | **Resolved → ADR-0004** — iterative-conjugate validation protocol | `data/registry/cross_references.json` · `data/registry/graveyard_registry.json` · `data/verification/pead_verification_results.json` · `docs/RESEARCH_REGISTRY.md` · `docs/research/RR-Y1-016-C-x1-descriptive-asymmetry.md` · …and 25 more |
| PM-1 | 21 | **Resolved → ADR-0008** — idle capital defaults to fully invested | `data/registry/cross_references.json` · `data/registry/graveyard_registry.json` · `docs/RESEARCH_REGISTRY.md` · `docs/engine/OPERATOR_GUIDE.md` · `docs/research/RR-Y1-005-TEST-MOTORU-TASARIM-v-0-2.md` · …and 16 more |
| DEC-045 | 11 | Definition unrecoverable | `docs/DECISIONS.md` · `docs/RESEARCH_REGISTRY.md` · `docs/exposure_test/STAGE0_exposure_regime_preregistration.json` · `docs/research/D-187-exposure-rapor.md` · `docs/research/RR-Y1-005-TEST-MOTORU-TASARIM-v-0-2.md` · …and 6 more |
| DEC-044 | 8 | Definition unrecoverable | `CHANGELOG.md` · `docs/DECISIONS.md` · `docs/research/D-186-trend-duzeltme-rapor.md` · `docs/trend_test/STAGE0_d186_preregistration.json` · `src/screening/trend_d186.py` · …and 3 more |
| DEC-049 | 6 | Definition unrecoverable | `docs/RESEARCH_REGISTRY.md` · `docs/engine/OPERATOR_GUIDE.md` · `docs/research/RR-Y1-009-VERDICT-CONFIDENCE-LOCKBOX.md` · `src/engine/confidence.py` · `src/engine/config.py` · …and 1 more |
| DEC-014 | 5 | Definition unrecoverable | `docs/RESEARCH_REGISTRY.md` · `docs/research/RR-032-V3-OPENSOURCE-VE-SMART-MONEY.md` · `docs/research/RR-037-smartmoney-veri-erisim.md` · `src/analytics/brinson_attribution.py` · `src/signals/layers/viop_layer.py` |
| DEC-054 | 4 | Definition unrecoverable | `data/registry/graveyard_registry.json` · `docs/RESEARCH_REGISTRY.md` · `docs/yol1/CONSISTENCY_AUDIT.md` · `docs/yol1/LOCALIZATION_REPORT.md` |
| DEC-064 | 4 | **Resolved → ADR-0006** — ideal/realistic dual-measurement layer | `docs/RESEARCH_REGISTRY.md` · `docs/research/RR-Y1-027-frictionless-layer.md` · `src/engine/frictionless.py` · `tests/test_engine_frictionless.py` |
| DEC-035 | 3 | Definition unrecoverable | `docs/DECISIONS.md` · `docs/yol1/CONSISTENCY_AUDIT.md` · `docs/yol1/LOCALIZATION_REPORT.md` |
| DEC-018 | 1 | Definition unrecoverable | `docs/specs/SPEC_IC_FRAMEWORK_1.md` |
| DEC-024 | 1 | Definition unrecoverable | `docs/features/IC_FRAMEWORK.md` |
| DEC-025 | 1 | Definition unrecoverable | `docs/features/RISK_LAYER.md` |
| DEC-055 | 1 | Definition unrecoverable | `scripts/verification/verify_pead_stage0.py` |

## The unrecoverable rows

These identifiers are cited but their intent cannot be reconstructed from what survives. The
citation is left in place rather than rewritten, because a reference to a decision that was
never written down is a true statement about this project's history. Promote one to an ADR only
if a future decision makes it load-bearing *and* its intent is recoverable from evidence — not
from a guess about what the number once meant.

Resolved rows keep their citations unchanged for now; rewriting call sites from the old
identifier to the new `ADR-NNNN` is a separate pass.
