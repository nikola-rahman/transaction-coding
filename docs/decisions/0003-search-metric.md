# 0003: Use AURC as the search metric

Status: accepted, 2026-11-06

## Decision

The architecture search optimizes AURC, the area under the risk-coverage curve, on development data. Lower is better.

Candidates must also stay within a calibration limit, and within latency and serving cost limits. The limits are set after the baselines.

## Why

- The business question is how much can be automated at an acceptable error rate.
- Each company sets its own error limit, so one fixed limit would be arbitrary. AURC covers every limit.
- It rewards both accuracy and knowing when the model is unsure.
- It needs no cost assumptions, which are the weakest numbers in the project.
- It is less noisy than a single point on the curve.

## Reporting

The write-up uses business language: automation at 1%, 2%, 5%, and 10% error, plus cost per 1,000 transactions across a range of assumptions. Top-1 and top-5 accuracy are reported for every method.

## Limit

AURC includes parts of the curve no customer would use, such as automating everything. If the search gains there without improving useful error limits, we restrict the metric to that range.
