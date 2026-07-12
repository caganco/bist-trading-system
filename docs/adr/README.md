# Architecture Decision Records

Records of architectural and strategic decisions. Each record states the context, the options
considered (including the strongest rejected alternative), the decision, and its consequences.

Lifecycle: Proposed -> Accepted -> (Superseded-by ADR-NNNN | Deprecated). There is no Deleted
state. Once Accepted, a record's body is frozen; a decision is changed by writing a new record
that supersedes it. Immutability is enforced in CI.

Naming: `ADR-NNNN-title.md`, monotonic, never reused.

## Contents

[INDEX.md](INDEX.md) lists all ten records. [ADR-0000](ADR-0000-adopt-decision-records.md)
establishes the practice; ADR-0003 through ADR-0009 are a bounded backfill of decisions that
were already in force and referenced across the codebase, but had never been written down.

The invariants these records establish are collected in
[`../disciplines.md`](../disciplines.md).

## Dangling identifiers

[GHOST_DEC_INVENTORY.md](GHOST_DEC_INVENTORY.md) tracks decision identifiers that are cited but
have no record. Four are now resolved to ADRs. The rest are marked *definition unrecoverable* and
left as honest dangling pointers — a reference to a decision that was never written down is a
true statement about this project's history, and inventing a record to cover it would not be.

The earlier decision store lives in [`../decisions/`](../decisions/) and
[`../DECISIONS.md`](../DECISIONS.md). Both are retained for history and superseded by this
discipline.
