# ADR-0003: Two-track portfolio architecture

- **Status:** Accepted
- **Date:** 2026-07-12
- **Supersedes:** none
- **Superseded-by:** none
- **Related:** ADR-0007

## Context
The project pursues a real return above a market-and-inflation floor with a single small account.
Two goals sit in tension: capturing broad market return reliably, and searching for a genuine
systematic edge. Treating both as one undifferentiated effort risks letting an unproven search
jeopardise the reliable base, or letting the reliable base mask the absence of a real edge.

## Options Considered
- **Single blended strategy.** Rejected: an unvalidated signal and the passive base share one
  book; a drawdown in the search corrupts the anchor, and forgone base return is hidden.
- **Search only, no passive anchor.** Rejected: leaves the portfolio fully exposed to the outcome
  of a search that may never produce a validated edge; the dominant loss channel becomes
  forgone market return.
- **Two separated tracks (chosen).** A passive, validated anchor (Yol-2) that captures broad
  return, and a separate research track (Yol-1) that searches for edge under strict validation.

## Decision
Maintain two structurally separated tracks. **Yol-2** is a passive, smart-beta anchor: validated,
live, and the portfolio's reliable base. **Yol-1** is a systematic research track whose outputs
reach capital only after independent validation. The anchor is not put at risk by the search.
Later market expansions (see ADR-0002) are additions to the research track and do not touch the
anchor.

## Consequences
- **Positive:** the reliable base is insulated from research outcomes; the cost of an empty
  search is bounded.
- **Accepted cost:** the anchor's return sets a hard benchmark the research track must beat net
  of costs, which is deliberately difficult.
- **Follow-up:** any new track inherits this separation.

## Invariants
The passive anchor is never placed at risk by an unvalidated research result.
