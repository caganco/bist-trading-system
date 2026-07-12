# ADR-0007: Research-record status classification and permanence

- **Status:** Accepted
- **Date:** 2026-07-12
- **Supersedes:** none
- **Superseded-by:** none
- **Related:** ADR-0004, ADR-0006

## Context
A research programme accumulates closed candidates. If closed results can be quietly revived or
deleted, the record stops being trustworthy and the same dead ends are re-run. After seven
independent probes, the project reached a structural finding — an edge is either where the
operator cannot reach it, or, where reachable, already priced — and this needed a permanent,
legible classification rather than scattered notes.

## Options Considered
- **Keep only positive results.** Rejected: *not detected* is knowledge; discarding it invites
  repetition and hides the shape of the search space.
- **Allow revival of closed candidates.** Rejected: destroys the meaning of a negative result and
  invites motivated reopening.
- **Permanent status ladder (chosen).**

## Decision
Every candidate carries an explicit status. A formally failed confirmation, or full-universe
contamination, is a **graveyard** entry — permanent and never revived. A candidate blocked by an
access wall, a power limitation, or an untested mechanism — with no formal failure — is
**save/wait**, which may be revisited under a future clean universe. A real-but-untradeable
effect is a **friction-grave** (ADR-0006). Negative results are recorded as carefully as positive
ones.

## Consequences
- **Positive:** the search space is legible; dead ends are not re-run; honesty about *not
  detected* is preserved.
- **Accepted cost:** discipline is required to record negatives with the same rigour as positives.
- **Follow-up:** the register distinguishes the three statuses explicitly.

## Invariants
Graveyard entries are permanent. Save/wait is not graveyard. Sign-flipping a failed result is
prohibited.
