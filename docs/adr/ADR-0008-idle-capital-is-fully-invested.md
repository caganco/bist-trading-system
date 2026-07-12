# ADR-0008: Idle capital defaults to fully invested (forgone-return discipline)

- **Status:** Accepted
- **Date:** 2026-07-12
- **Supersedes:** none
- **Superseded-by:** none
- **Related:** ADR-0003
- **Resolves ghost:** PM-1 (referenced with no prior record)

## Context
In a long-only constrained programme, the largest loss channel is not a bad trade but capital
sitting idle while the market rises. A signal that gates cash in and out can lose far more to
forgone market return than it gains from selection.

## Options Considered
- **Let signals gate cash (hold cash when unsure).** Rejected: forgone market return dominates
  the loss budget in the long-only setting.
- **Fully invested by default, signals tilt within the invested book (chosen).**

## Decision
Signals never gate cash. The default state is fully invested; a signal expresses itself as a tilt
within an already-invested book, not as a move to cash. Forgone market return is treated as the
dominant loss channel and measured explicitly.

## Consequences
- **Positive:** the dominant loss channel is controlled by construction.
- **Accepted cost:** the book stays exposed to market drawdowns by default; risk control operates
  within the invested book, not via cash.
- **Follow-up:** measurement reports forgone return alongside selection return.

## Invariants
Signals do not gate cash; idle equals fully invested.
