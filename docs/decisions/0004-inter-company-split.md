# 0004: Standard format and whole-organization split

Status: accepted, 2026-11-06

## Decision

All sources use one shared record format, modelled on a spend platform's transaction record. Missing fields stay null, and no values are invented. Records keep their source, and they are not presented as any company's data.

The foundation model is an inter-company task, so its splits hold out whole organizations.

- Train: Los Angeles, Ramsey County, and the remaining Connecticut bodies.
- Validation: Fulton County, Connecticut Green Bank, CT Lottery, Connecticut Airport Authority, and Cambridgeshire.
- Sealed test: Calderdale and Barnet.

Intra-company results, such as lookup and per-customer learning, are always labeled separately.

## Why

An earlier random split let 71% of validation rows repeat a merchant and account pair from training, which inflated scores.

## Limit

Few organizations are available, and two supply most rows, so inter-company results are noisy.
