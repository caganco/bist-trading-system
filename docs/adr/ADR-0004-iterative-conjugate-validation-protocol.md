# ADR-0004: Iterative–conjugate validation protocol

- **Status:** Accepted
- **Date:** 2026-07-12
- **Supersedes:** none
- **Superseded-by:** none
- **Related:** ADR-0007, ADR-0009
- **Resolves ghost:** DEC-053 (referenced in ~30 files with no prior record)

## Context
A candidate signal can be tuned until it fits one sample; the fit then fails out of sample. The
project needs a protocol that permits iteration during development while keeping a genuinely
independent test that iteration cannot leak into. This decision was in force and referenced
across the research records but had never been written down.

## Options Considered
- **Single in-sample development with a goodness score.** Rejected: no independent confirmation;
  the score is itself optimised against.
- **Full cross-validation everywhere.** Rejected for the confirmation step: repeated looks at the
  same data reintroduce multiplicity; a held-out single-shot test is stronger where affordable.
- **Iterative development on one split, single-shot confirmation on a frozen second split
  (chosen).**

## Decision
Develop iteratively on a first sample (X₁) with a bounded number of attempts; confirm once on a
second sample (X₂) that is frozen before it is seen, with no tuning against it. A failed X₂ test
retires the candidate permanently. Sample independence between X₁ and X₂ is non-negotiable.
Regime-independence is not required: a regime-dependent factor is legitimate if an ex-ante
now-cast of the regime is feasible. Sign-flipping a failed result into its opposite is prohibited.

## Consequences
- **Positive:** iteration stays honest because the confirmation sample is untouched until the end.
- **Accepted cost:** each candidate consumes a scarce independent sample; the attempt budget is
  deliberately small.
- **Follow-up:** an optional independent review layer may precede the confirmation step.

## Invariants
X₁/X₂ sample independence is absolute. A failed confirmation retires the candidate; retired
candidates are permanent (ADR-0007). Thresholds freeze before the result is seen (ADR-0009).
