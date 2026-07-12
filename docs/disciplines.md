# Discipline Register

Standing invariants the project holds itself to. Each is defined once here rather than restated
inline, and cites the decision record that established it. Disciplines are semi-stable: a change
is made by superseding the establishing decision, not by silent edit.

| ID | Discipline | Established by |
|---|---|---|
| DISC-01 | A load-bearing architectural or strategic decision is not put in force without a decision record. | ADR-0000 |
| DISC-02 | The passive anchor is never placed at risk by an unvalidated research result. | ADR-0003 |
| DISC-03 | X₁/X₂ sample independence is absolute; a failed confirmation retires a candidate permanently. | ADR-0004 |
| DISC-04 | Committed engine contracts are not broken and superseded code is not deleted; mathematical bug fixes are the sole, explicit exception. | ADR-0005 |
| DISC-05 | The ideal measurement report is non-verdict and never justifies deployment; causal invariants are never relaxed. | ADR-0006 |
| DISC-06 | Graveyard entries are permanent; save/wait is distinct from graveyard; sign-flipping a failed result is prohibited. | ADR-0007 |
| DISC-07 | Signals do not gate cash; idle equals fully invested; forgone return is measured. | ADR-0008 |
| DISC-08 | Evidence order is measured data > research > critique > intuition; one question is resolved once. | ADR-0009 |
| DISC-09 | Pre-registered thresholds freeze before a result is seen; post-hoc loosening is prohibited. | ADR-0009 (via ADR-0004) |
| DISC-10 | Measurement windows are fixed ex-ante; no ex-post peak selection (look-ahead tautology). | ADR-0004 |
| DISC-11 | The public repository contains only production-grade artifacts; internal-process vocabulary is excluded and enforced in CI. | ADR-0001 |

> Entries above are seeded from the resolved decision records. Additional inline disciplines
> referenced across the research records are folded in here as their establishing records are
> written; none is left defined only inline.
