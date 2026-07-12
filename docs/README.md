# Documentation Guide

What lives where, and why. This map describes the tree as it actually is — including the parts
that are still being reorganised.

## The four layers

| Layer | Lives in | Holds | Rule |
|---|---|---|---|
| **Decisions** | [`adr/`](adr/) | Architecture decision records (`ADR-NNNN`) | Immutable once accepted. A decision is changed by superseding it, never by editing it. |
| **Evidence** | [`research/`](research/), [`yol1/`](yol1/) | Research records (`RR-`, `NRR-`, `D-`), pre-registrations, results, graveyard | Append-only. A finding that turned out wrong is marked, not deleted. |
| **Disciplines** | [`disciplines.md`](disciplines.md) | Standing rules every measurement must satisfy (`DISC-NN`) | Violating one does not weaken a result; it invalidates it. |
| **Specs & guides** | [`specs/`](specs/), [`guides/`](guides/), [`features/`](features/) | Component specifications, operational how-tos, feature state | Living documents. Edited in place. |

The distinction that matters: **decisions and evidence accumulate, specs and guides get
rewritten.** If a document would be *wrong* to change after the fact, it belongs in the first
two rows.

## Evidence: how research records are classified

Every record in `research/` carries a status header on its first line. There are three:

- **(no header) — current.** The `RR-Y1-*` series, `NRR-007`/`NRR-008`, and everything in
  `yol1/`. These reflect the engine as it stands.
- **`SUPERSEDED-LINEAGE`.** Written against an earlier architecture that no longer exists.
  Retained because the reasoning and the negative results are still worth reading; not a guide
  to the current system.
- **`data-feasibility`.** Asks whether a data source exists and can be pulled, which is
  independent of whatever architecture consumes it. These stay valid across rewrites and several
  are still cited by current work.

A record whose class could not be settled from its content is marked `needs-review` rather than
guessed at.

[`RESEARCH_REGISTRY.md`](RESEARCH_REGISTRY.md) is the master index: every record, its ID, date,
and status. **A new research record is not finished until it has a row there.**

## Identifiers

`ADR-NNNN` decisions · `RR-…` / `NRR-…` / `D-…` research · `DISC-NN` disciplines.

All are monotonic and never reused. Where a document is renamed, the old name is recorded in the
file so inbound references stay traceable.

## Known gaps

Stated here rather than left for a reader to trip over:

- 10 of the 14 dangling decision identifiers are still dangling. Four are resolved to ADRs — the
  three heaviest among them, which accounted for most of the dangling references in the tree. The
  other ten are marked *definition unrecoverable* in
  [`adr/GHOST_DEC_INVENTORY.md`](adr/GHOST_DEC_INVENTORY.md) and are left as honest dangling
  pointers rather than covered with invented records.
- Call sites still cite the old identifiers. Rewriting them from `DEC-NNN` to the `ADR-NNNN` that
  now defines them is a separate pass.
- ADR immutability is not yet enforced in CI. The records are `Accepted` and are meant to be
  frozen; the guard that makes that binding comes next.
- The earlier decision store (`decisions/`, `DECISIONS.md`) is retained and superseded, not
  migrated. It is history, not a second source of truth.
- A few operational documents (`DATA_HUB.md`, `PRE_COMMIT_SETUP.md`, `SIGNAL_ALERT_USAGE.md`,
  `engine/OPERATOR_GUIDE.md`) and two one-off audits (`AUDIT_REPORT_001.md`,
  `CODEBASE_INVENTORY_v2.md`) still sit at the top level and have not been homed.
