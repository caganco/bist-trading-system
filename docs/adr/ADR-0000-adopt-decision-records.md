# ADR-0000: Adopt Architecture Decision Records

- **Status:** Accepted
- **Date:** 2026-07-12
- **Supersedes:** none
- **Superseded-by:** none
- **Related:** ADR-0001 through ADR-0009

## Context
The project is developed continuously over many working sessions. The rationale behind a
decision — why it was made and which alternatives were rejected — tends to be lost over time,
leaving references that point nowhere. An audit found decisions referenced dozens of times across
the codebase with no surviving written record. Because the repository is public and serves as a
worked record, decision history should also be legible to an outside reader. A durable decision
format is adopted now, before further expansion, so the record does not degrade further.

## Options Considered
- **Continue with free-text decision notes.** Rejected: no structure, no immutability, no
  lifecycle; the reason an alternative was rejected is recorded inconsistently, and references
  drift into dangling pointers.
- **An external wiki or tool.** Rejected: out of the repository, unversioned, not enforceable in
  CI.
- **Repository-hosted Architecture Decision Records with CI-enforced immutability (chosen).**

## Decision
Adopt Architecture Decision Records under `docs/adr/`, with CI-enforced immutability. Load-bearing
prior decisions are consolidated into records through a bounded backfill; new architectural or
strategic decisions are recorded as ADRs from now on. Decisions referenced but never written down
are resolved where reconstructable and otherwise left explicitly as unrecoverable rather than
fabricated.

## Consequences
- **Positive:** decision rationale is auditable and durable; dangling references are closed; the
  public record is legible.
- **Accepted cost:** a short authoring step for each load-bearing decision; a CI guard to maintain.
- **Follow-up:** the backfill is a one-time bounded task; remaining referenced-only decisions stay
  catalogued until a future decision makes one load-bearing.

## Invariants
A load-bearing architectural or strategic decision is not put in force without a record. Record
immutability extends the project's existing treatment of committed work to the decision layer.
