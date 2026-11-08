# 0008: "Safe to approve" needs both the next step and the account confidence

Status: accepted, 2026-11-08

## Decision

A suggestion is marked safe to approve only when both hold:

1. The model's most likely next step is "approve".
2. The model's confidence in the suggested account is at least 0.9.

A matching company rule is always safe. Everything else is shown for review, with the model's suggested next step.

## Why

- The next-step head and the account head are trained as separate questions, and they can disagree. Error analysis found rows where the next step was "approve" while account confidence was below 0.3. Using the next step alone accepted far more wrong codes.
- Account confidence alone ignores the reasons the next step captures, such as a generic retailer where only a receipt can settle the account.

## Evidence

| | Development | Test |
|---|---|---|
| Marked safe | 405 of 1,000 | 85 of 400 |
| Wrong among those | 2 (0.5%) | 7 (8.2%) |

## Limit

The 0.9 threshold was chosen on development organizations. On the two test councils, confidence was too high: 8.2% of safe suggestions were wrong, and one council accounts for 6 of the 7. A deployment should set the threshold for each company from its own recent approvals and corrections, and recalibrate when the monitored error rate rises.
