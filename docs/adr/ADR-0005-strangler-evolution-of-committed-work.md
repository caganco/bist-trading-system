# ADR-0005: Strangler evolution of committed work

- **Status:** Accepted
- **Date:** 2026-07-12
- **Supersedes:** none
- **Superseded-by:** none
- **Related:** ADR-0000

## Context
A measurement engine that produces verdicts must be trustworthy over time. Rewriting committed
engine paths in place risks silently changing past results and destroying the ability to
reproduce them.

## Options Considered
- **Edit committed paths in place when behaviour changes.** Rejected: breaks reproducibility and
  erases the evolution record.
- **Freeze the engine entirely.** Rejected: legitimate corrections (notably mathematical bug
  fixes) must be possible.
- **Strangler evolution (chosen):** new behaviour is added alongside; committed paths are not
  broken and old code is not deleted.

## Decision
Committed engine contracts are not broken and superseded code is not deleted; new behaviour is
added additively. History is retained as part of the system's evolution. A narrow exception
applies to genuine mathematical bug fixes, which are legitimate and marked explicitly rather than
made silently.

## Consequences
- **Positive:** past results stay reproducible; the evolution is auditable.
- **Accepted cost:** additive layers accumulate; periodic consolidation is needed.
- **Follow-up:** golden byte-stability gates protect committed outputs.

## Invariants
Committed engine contracts are not broken; superseded code is retained. Mathematical bug fixes
are the sole exception and are never silent.
