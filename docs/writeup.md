# Coding business transactions from company history

A five-minute read: the business result first, then accuracy, how it was built, how it was measured, what goes wrong, and what is still missing.

## The problem

Every company records each card or bank transaction under an account from its own chart of accounts. Assigning that account is called coding. It piles up at month-end, and most of it is repetitive.

A suggestion engine helps in three ways:

1. **Pre-fill the right account,** so the person only approves.
2. **Make a wrong suggestion a one-click fix,** with the right account in a short list.
3. **Say when it does not know,** and what would settle it: a receipt, the spender, a merchant lookup, or a bookkeeper.

Every company's chart is different, and the same merchant is coded differently by different companies. So the system learns from each company's own history rather than from one global mapping.

## Business result

**Review time per 1,000 transactions.** These are estimates from stated assumptions, not measurements:

| | No suggestions | Vendor rules | Model |
|---|---|---|---|
| Development organizations | 8.3–16.7 h | 3.4–6.9 h | **1.8–3.7 h** |
| Test councils | 8.3–16.7 h | 4.6–9.2 h | **2.1–4.2 h** |
| Wrong codes approved on a skim | 0 | 0 | 2 per 1,000 (development), 18 per 1,000 (test) |

The assumptions, in seconds per transaction:

| Action | Seconds |
|---|---|
| Code from scratch | 30–60 |
| Approve a shown suggestion | 3–6 |
| Skim a suggestion marked safe | 1–2 |
| Fix from the top 5 | 10–20 |
| Search the chart | 30–60 |

The model roughly halves review time compared with vendor rules. Marking suggestions safe is what lets a person skim, and that is also the only way a wrong code gets through unnoticed. So the next question is how many transactions can be skimmed at a given error rate.

**Automation against error.** Each row is one confidence threshold, used together with the model's next step being "approve". The thresholds are chosen on development and applied unchanged to the test councils. The demo app and the review-time estimate above use the fixed threshold of 0.9 in the first row.

| Threshold | Development: skimmed | Development: wrong | Test: skimmed | Test: wrong |
|---|---|---|---|---|
| **0.90, the app's safe-to-approve rule** | **40%** | **0.5%** | **21%** | **8.2%** |
| 0.87, chosen for 1% error on development | 42% | 1.0% | 25% | 11.0% |
| 0.81, chosen for 2% error on development | 46% | 1.7% | 29% | 13.9% |
| 0.57, chosen for 5% error on development | 55% | 4.9% | 42% | 18.9% |
| 0.05, chosen for 10% error on development | 59% | 7.5% | 55% | 28.9% |

On organizations like the development set, about 40–45% of transactions can be skimmed at 1–2% error. On the two test councils, the same threshold lets far more errors through. Confidence learned on one kind of organization does not carry over unchanged.

**Calibration per company.** Each company's threshold was fitted on its own first half of transactions, in date order, and applied to the second half:

| Target error 2% | One threshold for all | Threshold per company |
|---|---|---|
| Development: skimmed / wrong | 45% / 1.8% | 40% / 1.0% |
| Test: skimmed / wrong | 29% / 13.8% | 8% / 6.2% |

Per-company calibration cuts the error on the test councils by more than half. But with only 100 reviewed transactions per council, the safe share drops to 8%, and the error is still above target. In practice a new company should start with every suggestion shown for review. Skimming opens up as its approvals and corrections build a reliable threshold.

## Accuracy against vendor rules

Measured on organizations never used in training, with each transaction seeing only the company's earlier history:

| | Development (5 organizations, 1,000 transactions) | Test (2 councils, 400 transactions) |
|---|---|---|
| Vendor rule: merchant goes to its usual account | 65.3% | 49.8% |
| **Model: first suggestion right** | **71.9%** | **59.2%** |
| Model: right account in the top 5 | 87.6% | 87.5% |

By organization:

| Organization | Vendor rule | Model |
|---|---|---|
| Cambridgeshire County Council | 45.5% | 62.0% |
| CT Lottery | 79.5% | 80.5% |
| Connecticut Airport Authority | 73.5% | 79.0% |
| Connecticut Green Bank | 62.5% | 65.5% |
| Fulton County | 65.5% | 72.5% |
| *Test:* Calderdale Council | 50.0% | 61.0% |
| *Test:* Barnet Council | 49.5% | 57.5% |

**Where the gain comes from:**
- **New merchants (18% of transactions).** No rule can fire, and the model is right on 25–29% of them from the merchant name, category and department.
- **Merchants coded several ways.** Where a rule exists, the model is right 82.4% of the time against the rule's 79.9% on development, and 66.1% against 60.9% on test.
- **Consistent merchants** (3+ uses, at least 80% to one account) are where a rule matches or beats the model: 93.7% against 92.2% on development. So the design runs company rules first and uses the model for everything else.

The gain is largest where coding is messiest. Card spend at councils is mostly generic retailers such as Tesco, Amazon and Argos, and at the two test councils the rule is right only about half the time.

## How it works

1. **Rules first.** A company rule (merchant text → account) wins, and the model is not asked.
2. **Retrieve history as of that date.** Up to 20 earlier transactions of the same company are picked by exact matches, in this priority order:
    1. same merchant and department
    2. same merchant
    3. same merchant category and department
    4. same merchant category
    5. same department

   Each comes with the account it was coded to.
3. **Ask the model two questions in one prompt.** The prompt holds the transaction (merchant, amount, date, department, merchant category, memo), the retrieved history and the company's accounts. The questions are "which account?" and "what next step?". A fine-tuned Qwen3-4B with a LoRA adapter and a decision head gives a probability for every option.
4. **Mark it safe to approve** only if the next step is "approve" and account confidence is at least 0.9. Otherwise, show it for review with the suggested next step.

Training used real coded transactions from 10 public bodies, plus next-step labels:
- **Real rows:** labelled by LLM labellers against a written rubric.
- **28 generated companies:** LLM agents wrote each company's chart and vendors, and code sampled the transactions and applied the rubric.

## Evaluation

- **Organizations are split whole.** Train, development and test share no organization. An earlier random split let 71% of validation rows repeat a merchant and account pair seen in training.
- **Test set:** two UK councils, Calderdale and Barnet, held out of training and development ([protocol](../results/test/protocol.md)).
- **History is rolling.** An earlier version froze history at each organization's first 1,000 transactions. That understated development accuracy by about 10 points (62.2% to 71.9%), because months-old history hid recent changes in coding. Fixing it was the largest single improvement in the project, and it came from the evaluation, not the model.
- **Confidence intervals** come from Wilson intervals for rates, and a paired bootstrap for the gain over the rule.
- **Two training seeds were compared.** They reach the same accuracy but differ on 18% of individual answers. Gaps of 2–3 points between training variants were noise.

**Next step.** The labels come from LLM labellers, so this measures agreement with a labeller, not correctness. Two labellers agreed with each other on 85 of 100 rows. On 330 real transactions from two held-out organizations:

| Method | Agreement with the labeller |
|---|---|
| Always "approve" | 54% |
| Model trained on real labels only | 62% |
| Model trained on real and generated labels | 79–81% (two seeds) |

**Safe to approve:** see [automation against error](#business-result). With the app's rule, 2 of 405 safe suggestions were wrong on development and 7 of 85 on test.

## Error analysis

Every wrong suggestion was put in one group, using only the history the model was shown:

| Why it was wrong | Development (281 wrong) | Test (163 wrong) |
|---|---|---|
| **Inconsistent coding:** history pointed to another account | 37 | 24 |
| **Inconsistent coding:** mixed history, right answer was a minority | 63 | 65 |
| **Insufficient information:** new merchant, no history | 132 | 51 |
| Near-duplicate account names | 26 | 6 |
| **Model missed:** history pointed to the right answer | 23 | 17 |

About 90% of errors come from the data, not the model. Either the company coded the same merchant inconsistently, or nothing available at coding time could settle the account. Three test examples show the pattern:

- **The council changed its own habit.** Calderdale paid "Hotel on Booking.com" £36.67. Every earlier Booking.com payment had been coded *expenses*, and the model suggested *expenses* at 95% confidence, marked safe to approve. This time the council recorded *miscellaneous expenses*. The same department had recently switched its hotel stays to that account, but at a different merchant.
- **The label disagrees with all of the history.** Barnet's £10 "STUDEN PHOTOCARD" had gone to *travelling expenses* 4 times out of 4. The model followed at 99% confidence, and the recorded account was *other transfer payments*.
- **Mixed history.** Barnet's earlier Sainsbury's purchases were split between *food costs* (8) and *equipment and materials* (7). The model said *food costs* for a £7 purchase, and the council recorded *equipment and materials*. Only a receipt can say which one it was.

No model can learn these from the data shown. That is why the system suggests a next step instead of guessing silently:
- **Most errors are routed:** 84% of development errors and 61% of test errors went to a next step rather than "approve".
- **The right account is usually close:** it was in the top 5 for 56% of development errors and 69% of test errors, so the fix is one click.

The remaining model misses are mostly near-ties, like a merchant coded 8 times one way and 8 times the other.

## Data

All data is public:

| Source | Organizations | Role |
|---|---|---|
| Connecticut state and quasi-public agency payments (`data.ct.gov`) | 13 bodies | Train (8), next-step evaluation (2, held out of training), development (3) |
| Los Angeles City controller (`controllerdata.lacity.org`) | 1 | Train |
| Ramsey County, MN (`data.ramseycountymn.gov`) | 1 | Train |
| Fulton County, GA (`data.fultoncountyga.gov`) | 1 | Development |
| UK council purchase-card files (`data.gov.uk`) | Cambridgeshire, Calderdale, Barnet | Development (Cambridgeshire), test (Calderdale, Barnet) |

The split is in [`results/split.json`](../results/split.json). The test councils were held out of training and development ([`results/test/protocol.md`](../results/test/protocol.md)). Results measure agreement with what public bodies recorded. They are not startup spend, and recorded codes are sometimes inconsistent or wrong.

## Limits

- **The data is public-sector spend.** Councils and agencies have fine-grained charts and noisy labels, and no SaaS, payroll or inventory structure. The results show the method works across organizations, but they do not estimate a startup's automation rate.
- **Results measure agreement with recorded codes.** Some recorded codes are wrong or inconsistent.
- **Errors are counted, not weighted by amount.** Most test errors are under £75, while the costly class is balance-sheet items such as loans coded as expenses. A deployment should report errors weighted by value and treat large or balance-sheet items separately.
- **Retrieval matches merchant text exactly,** so "B.com" and "Hotel on Booking.com" count as different merchants. Normalizing merchant names would improve the history the model sees.
- **Next-step quality is agreement with an LLM labeller,** checked by hand only on samples.

## What a deployment would add

- **A per-company threshold that starts strict:** show everything for review until the company has enough approvals to fit its own threshold, then refit it as corrections come in.
- **Monitoring per company:** the rate at which people change suggestions, the error rate in a random audit of approved codes, confidence drift, and the share of new merchants.
- **Recalibrating or retraining only when needed.** A correction already takes effect through history, without retraining. Recalibrate when calibration drifts for one company, and retrain only when the drop shows up across many.
- **A trace on every suggestion:** model version, retrieved transactions, probabilities, and source (rule, model, person).
- **Receipts and memos as inputs.** They settle most generic-retailer purchases.
