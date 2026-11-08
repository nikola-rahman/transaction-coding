# 0005: Focus on intra-company coding

Status: accepted, 2026-11-06

The project works on one task: a coder that learns from a company's own history, plus a sync guard that flags risky suggestions. New-customer cold start and the foundation model are out of scope, and rows with no usable history go to a person.

Why: coding products describe suggestions that learn from a business's own coding, our data supports this task, and no-history attempts did not transfer.

Results are reported by amount of company history, so no large labeled set is assumed.
