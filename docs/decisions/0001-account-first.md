# 0001: Predict Account first, with other attributes in the data model

Status: accepted, 2026-11-06

## Decision

The data model and simulator store every coding attribute, including Account, Department, and Vendor. The first models, baselines, and reported results predict Account only.

## Context

A transaction can need several accounting attributes, such as Account, Department, and Vendor. Spend platforms' public material describes coding suggestions for several of them.

## Options

| Option | Benefit | Cost |
| --- | --- | --- |
| Account only, in data and models | Simplest | Adding attributes later would mean rebuilding much of the system |
| **Account first, others in the data model** | Focused now and extendable later | Slightly more simulator work up front |
| All attributes from the start | Closest to the product | Much more work, and harder to evaluate |

## Why this option

1. **Business impact.** The account determines where an amount lands in the financial statements. A wrong account is the error the project's cost model is built around.
2. **Real evaluation.** Council files contain expense codes, which can stand in for accounts. They offer little for testing Vendor as a ledger attribute. Account is the target both evaluation sets can test.
3. **Clean evidence.** One target gives one clear set of metrics. Several targets at once would make it harder to see what caused a result.
4. **Low regret.** Storing all attributes now keeps the later work to prediction and evaluation, without rebuilding data.

## What is assumption, not evidence

- We assume Department and Vendor are often easier, because the card, cardholder, or merchant can partly reveal them. This has not been measured.
- We assume Account errors cost more than Department or Vendor errors. Costs are assumptions throughout the project.
- We do not know how coding products prioritize these attributes, or how often customers use each one.

## Consequences

- The simulator generates all attributes, with source and timing for each.
- Headline results apply to Account only, and the write-up says so.
- The demo shows Account suggestions only, so it covers less than a full coding product would.
- Splits stay outside the first version, which detects likely splits and sends them to a person.

## Likely challenges and answers

**"Coding products suggest several attributes. Why only one?"** Account is the highest-stakes attribute and the one we can test on real data. The data model already holds the others, so this is sequencing, not a limit of the design.

**"Aren't attributes related? Predicting them together might work better."** Possibly. Knowing the department could help choose the account. Department can be an input where it is already set. Joint prediction is a good later experiment.

**"How do you know Account matters most?"** We don't know for any specific product. It is a reasoned assumption from how accounting works, and the first thing to revisit with real usage data.

## When to revisit

- Account results are stable and pass the evaluation.
- Evidence shows Department or Vendor drives more review time.
- Joint prediction looks likely to improve Account accuracy.
