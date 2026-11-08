# 0007: Evaluate with rolling history

Status: accepted, 2026-11-08. Replaces the fixed 1,000-transaction history used in earlier evaluations.

## Decision

Every evaluated transaction sees all transactions its organization coded before it, and none after. Retrieval, prompts and baselines all use this history.

## Context

Earlier evaluations gave each organization a fixed history: its first 1,000 transactions. Rows were then sampled from transactions 1,000 to 2,999. This made baselines cheap and comparable, but late rows used history up to 2,000 transactions old. For some organizations that gap was several months, which hid changes in how they coded.

In a product, history grows with every approved or corrected transaction, so the fixed snapshot measured a situation that does not happen.

## Effect

Same model, same development rows, only the history changed:

| | Fixed history | Rolling history |
|---|---|---|
| Development, first suggestion right | 62.2% | 71.9% |
| Development, right in top 5 | 78.4% | 87.6% |

## Limits

- Rolling history assumes a transaction's code is known as soon as it happens. In practice coding lags until review or close, so these numbers are slightly optimistic for transactions close together in time.
- The model was trained on rows with fixed-length history windows. Training on rolling history may help further. That has not been tested.
