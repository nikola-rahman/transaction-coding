# Action rubric, draft 1

Choose the next action for one transaction, using only what is known at coding time: the transaction, the account list, and similar past transactions. You do not know the recorded account.

Ask one question: what is the cheapest step likely to settle the account?

## Actions

### accept
Use when the evidence settles one account. For example:

- Past coding for this merchant, in the same context, consistently uses one account.
- The merchant's business plainly matches one account, and no other account is a reasonable fit.

Do not accept when the amount is unusual for this merchant, or when close alternatives exist.

### request_document
Use when knowing what was bought would settle it, and a receipt or invoice would show that.

- General retailers and marketplaces that sell many kinds of goods.
- Vendors whose past coding depends on the item or service.

### ask_person
Use when the purpose or beneficiary is the unknown, which a document would not show.

- Who the spending was for.
- Why it was bought, such as a staff meal or a client meal.

Use this only when a person who made or approved the spending can be identified or reached.

### lookup_merchant
Use when the merchant's business is unknown, and knowing it would probably settle the account.

- Unfamiliar names with no useful history.
- Truncated or unclear merchant text.

### send_to_bookkeeper
Use when the question needs accounting judgment, or the risk is high.

- Unusually large amounts for this organization, when the account is not settled.
- Possible capital purchases, loans, prepayments, deferred items, or reclassifications.
- Evidence that conflicts in a way a document or the spender is unlikely to resolve.
- Close accounts where company policy decides the answer.

## Priority

If more than one action fits:

1. Choose `send_to_bookkeeper` if accounting judgment or high risk is involved.
2. Otherwise, choose the cheapest action likely to settle it: `lookup_merchant`, then `request_document`, then `ask_person`.
3. If the amount is very small and the likely account is reasonable, prefer `accept`, unless the account would change how the spending is reported.

## Output

Return the action, what is unknown (`item`, `purpose`, `merchant`, `accounting_judgment`, or `nothing`), and a one-sentence reason based only on the rows shown.
