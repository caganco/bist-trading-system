# ADR-0006: Ideal and realistic dual-measurement layer

- **Status:** Accepted
- **Date:** 2026-07-12
- **Supersedes:** none
- **Superseded-by:** none
- **Related:** ADR-0004, ADR-0005, ADR-0007
- **Resolves ghost:** DEC-064 (referenced with no prior record)

## Context
A candidate can be economically real yet unharvestable: the phenomenon exists, but cost and
tradability destroy it in practice. A single realistic-cost measurement conflates *the effect
does not exist* with *the effect exists but cannot be captured*, and those require different
conclusions.

## Options Considered
- **Realistic-cost measurement only.** Rejected: cannot distinguish a genuinely absent effect
  from a real-but-untradeable one.
- **Frictionless measurement only.** Rejected: not a basis for any real decision.
- **Two reports from one causal pipeline (chosen).**

## Decision
Every measurement produces two reports from the same position series: a realistic report that
carries the verdict (full costs), and an ideal report that zeroes monetary friction (cost,
spread, execution timing, fill availability) while preserving the causal invariants — look-ahead
safety, survivorship, and the forward time-arrow. The ideal report is a non-verdict concept
ledger; it never justifies deployment. A strong-ideal, dead-realistic result driven by
tradability is classified as a friction-grave (retained for study), distinct from an
effect-absent graveyard entry.

## Consequences
- **Positive:** separates *no effect* from *real but uncapturable*; the shared pipeline shrinks
  the bug surface and yields a natural differential check.
- **Accepted cost:** two reports per run; the non-verdict label must be enforced so the ideal
  number is never promoted.
- **Follow-up:** verification checks confirm the causal layer is bit-identical between reports.

## Invariants
The ideal report is non-verdict. Monetary friction is zeroed; causal invariants are preserved and
never relaxed.
