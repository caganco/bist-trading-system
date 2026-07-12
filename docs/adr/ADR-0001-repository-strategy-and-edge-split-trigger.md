# ADR-0001: Repository strategy and edge-split trigger

- **Status:** Accepted
- **Date:** 2026-07-12
- **Supersedes:** none
- **Superseded-by:** none
- **Related:** ADR-0002

## Context
The research programme runs in a public repository. A validated, harvestable edge loses value once
its recipe is disclosed — a disclosed edge is a decayed edge. The shared infrastructure (the
measurement engine, validation protocol, and record system) is market-agnostic and benefits from
open development, but a confirmed signal's specifics must not be published. A policy is needed for
where work lives and at what point protection begins.

## Options Considered
- **A separate repository per market.** Rejected: the infrastructure and record system live in one
  place; a second repository means either duplication and drift, or a premature packaging effort,
  and it splits the record discipline.
- **Move everything to a private repository now.** Rejected: there is no harvestable edge to protect
  yet; the feasibility and infrastructure stage is not sensitive, and early privacy adds friction
  for no gain.
- **One repository with a module boundary and a predefined split trigger (chosen).**

## Decision
Market work lives in one repository behind a module boundary; the core engine stays
market-agnostic. Licensed data is never committed. **Split trigger:** at the moment any candidate
passes independent confirmation, that candidate's signal-specific layer — parameters, universe
filters, and signal code — moves to a private repository; the public repository retains only the
market-agnostic engine and the record system. The *existence* of a finding is recorded publicly;
its *recipe* is not. Before that point, feasibility, infrastructure, and negative results may
remain public, since publishing a negative result does not decay an edge.

## Consequences
- **Positive:** one infrastructure and record system; open development speed until a candidate is
  confirmed; automatic protection at the moment of confirmation.
- **Accepted cost:** a one-time relocation at confirmation, and two-repository boundary management
  from that point on.
- **Follow-up:** the private repository is not created until the trigger fires.

## Invariants
A confirmed signal's recipe is not held in the public repository. The disclosed-edge-decays
principle is applied to the project's own edge.
