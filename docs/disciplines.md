# Research Disciplines

Standing rules that every measurement in this repository must satisfy. They are not advice and
not per-study choices: a result that violates one is not a weaker result, it is an invalid one.

Disciplines are referenced by identifier (`DISC-NN`) from research records, pre-registrations,
and probe scripts. Today those references exist but the definitions do not — each one is
restated inline wherever it is used. This file is the register that ends that duplication.

## Status

**Stub.** Entries follow. The definitions are being backfilled from the research records that
currently carry them inline; until that lands, the authoritative wording of a discipline is the
one quoted in the record citing it.

## Format

Each entry:

    ## DISC-NN — <short name>
    **Rule.** One sentence, stated as a constraint.
    **Why.** The failure it prevents.
    **How it is checked.** The concrete test, gate, or review step that enforces it.
    **First stated in.** <research record>

Identifiers are monotonic and never reused. A discipline is retired by marking it superseded,
not by deleting it — the records that cite it must keep resolving.
