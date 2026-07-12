# Architecture Decision Records

Records of architectural and strategic decisions. Each record states the context, the options
considered (including the strongest rejected alternative), the decision, and its consequences.

Lifecycle: Proposed -> Accepted -> (Superseded-by ADR-NNNN | Deprecated). There is no Deleted
state. Once Accepted, a record's body is frozen; a decision is changed by writing a new record
that supersedes it. Immutability is enforced in CI.

Naming: `ADR-NNNN-title.md`, monotonic, never reused.

## Status

The directory is a scaffold. No records have been written yet — see
[GHOST_DEC_INVENTORY.md](GHOST_DEC_INVENTORY.md) for the decision identifiers that are
referenced from code and research but have no record behind them; backfilling those is a
separate piece of work.

Earlier decisions live in [`../decisions/`](../decisions/) and [`../DECISIONS.md`](../DECISIONS.md).
Both are retained for history and are superseded by this discipline.
