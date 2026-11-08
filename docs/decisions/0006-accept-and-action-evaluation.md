# 0006: How accept and action decisions are evaluated

Status: accepted, 2026-11-06

- Accept decisions are evaluated on real data, against recorded accounts.
- Next actions have no ground truth, so they are trained on subagent labels and generated examples, and evaluated on synthetic data and held-out agreement with subagent labels.
- The demo shows a few rows where the system does not accept, with its suggestion and action, so a viewer can judge whether they are sensible.
- The write-up states that action quality is judged for plausibility, because no product requirements or real outcomes exist.

Code performs all sampling and randomization. Subagents never see validation or test rows.
