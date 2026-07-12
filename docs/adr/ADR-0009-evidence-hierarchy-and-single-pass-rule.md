# ADR-0009: Evidence hierarchy and single-pass rule

- **Status:** Accepted
- **Date:** 2026-07-12
- **Supersedes:** none
- **Superseded-by:** none
- **Related:** ADR-0004
- **Resolves ghost:** DEC-039 (referenced in ~49 files with no prior record)

## Context
Different kinds of input carry different weight: a measured result, a piece of published research,
a critique, and an intuition are not equal evidence. Without an explicit ordering, an intuition
can quietly override a measurement, and the same question can be re-litigated repeatedly until it
returns the desired answer. This ordering was in force and was the single most-referenced
decision in the project, yet had no written record.

## Options Considered
- **Treat all inputs equally and decide case by case.** Rejected: lets the most confident voice,
  not the strongest evidence, win.
- **Intuition-led, evidence-checked.** Rejected: inverts the hierarchy; intuition becomes an
  authority rather than a hypothesis.
- **Explicit evidence hierarchy with a single-pass rule (chosen).**

## Decision
Evidence is ordered: **measured data > research > critique > intuition.** An intuition is a
hypothesis to be tested, not an authority. A given question is resolved in a single pass — one
question, one agent, once — rather than re-run until it yields a preferred answer.

## Consequences
- **Positive:** the strongest evidence wins by rule, not by confidence; questions are not
  re-litigated into a desired result.
- **Accepted cost:** intuitions must be converted into testable hypotheses before they carry
  weight, which is slower.
- **Follow-up:** the validation protocol (ADR-0004) operationalises this for candidate signals.

## Invariants
Measured data outranks research, critique, and intuition, in that order. Intuition is a
hypothesis, not an authority. One question is resolved once.
