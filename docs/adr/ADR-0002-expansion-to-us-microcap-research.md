# ADR-0002: Expansion to US micro-cap systematic research

- **Status:** Accepted
- **Date:** 2026-07-12
- **Supersedes:** none
- **Superseded-by:** none
- **Related:** ADR-0001, ADR-0007

## Context
The home-market research track reached a structural finding after seven independent probes: an
edge is either where the operator cannot reach it, or, where reachable, already priced (ADR-0007).
A feasibility analysis assessed which other markets have the thinnest combination of the two walls
— access and pricing-in — for a small solo account. US micro-cap long-only scored highest:
institutional capital is structurally excluded below liquidity thresholds, a small account fits
that capacity niche, documented anomalies concentrate on the long side (so a short constraint does
not block harvest), and data and execution infrastructure are mature. The base rate for retail
systematic trading is poor and is treated as a brake: changing markets does not create an edge, it
only indicates where one is structurally possible.

## Options Considered
- **US micro-cap long-only (chosen):** access is open, the edge is protected by institutional
  exclusion, long-side harvest clears the short constraint, infrastructure is mature.
- **Crypto delta-neutral funding/basis carry (deferred, not rejected):** a real structural effect,
  but domestic derivative access is restricted, pushing it offshore with legal-grey and
  counterparty exposure; independent evidence is cautious net of cost.
- **Futures, options, European, Japanese, FX markets:** access is adequate but the venues are
  efficient or carry higher data, cost, or language friction; small-scale documented edge is weaker
  than in micro-cap.

## Decision
Expand into US micro-cap long-only systematic research as a new track (records series RR-Y3). The
principle is **edge first, capital later:** capital is not moved until a candidate passes
independent confirmation, is positive net of conservative costs, separates currency beta from
alpha, and clears the real-return floor. This is an addition, not a migration: the passive anchor
is untouched. Phases run data-feasibility → infrastructure port → universe and data-quality probes
→ pre-registered measurement, with a pilot-capital decision held as a separate later step.

## Consequences
- **Positive:** a structurally-possible edge space after the home-market paradigm was exhausted;
  reuse of the market-agnostic engine in a second market.
- **Accepted cost:** a new data-licensing cost decision; currency-versus-alpha separation
  complexity; exposure to the poor retail base rate.
- **Follow-up:** if the same root wall (unreachable-or-priced) appears in the new market, it is
  classified into the status ladder as well — an expansion does not rescue an expansion.

## Invariants
The passive anchor is untouched. Capital is not moved before the pilot-capital step. All existing
research disciplines carry over unchanged. The repository split trigger (ADR-0001) is binding at
confirmation.
