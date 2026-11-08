# 0002: Build and measure on real public data, with no simulator

Status: accepted, 2026-11-06. Replaces an earlier plan to build a company simulator.

## Decision

Build and evaluate the system by replaying real public spending records in date order. Do not build a company simulator or a simulated human workflow for measurement.

## Why

- A full simulator requires too many assumptions about companies, policies, and behaviour.
- A simulated workflow also adds assumptions that the results would then reflect.
- In a small pilot on one council, a probe trained on 5,851 simulated rows scored 2.0% top-1, against 24.4% with the same number of real rows.

## The one assumption

If the system sends a transaction to a person, that person gives the code the organization actually recorded.

Cost and hours saved also depend on review time and error cost, which are shown as ranges.

## Consequences

- Measured results come from real coding decisions.
- Results describe public-sector spend, and cannot estimate a startup's automation rate.
- Recorded codes may be wrong, so results measure agreement with recorded codes.
- Reviewer behaviour, sync, unreviewed suggestions, and customer rules are not measured. They are covered as design notes, with no numbers.
- Any startup example in the demo is an illustration only, with no metrics.
- Council data is a real-data check for the method, and it does not shape product design or framing. System code contains no council-specific logic.
