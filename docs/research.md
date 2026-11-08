# Research notes

What was looked at before and during the build, and what each step changed.

## Product research

The design follows how business spend-management platforms describe their coding workflow in public help-center and API documentation. These pages were read by automated research agents, some as raw text and some through a tool that summarizes pages. No person has yet confirmed each statement against the live pages, so treat these as unconfirmed:

- Coding comes from manual codes, mapping rules, and default accounts.
- A suggestion feature fills empty accounting attributes on card and banking transactions on request, and leaves rules alone.
- People accept, dismiss, or override suggestions individually or in bulk.
- Suggestions stay in the platform until someone syncs to the ledger, and syncing can apply suggestions nobody reviewed.
- No public page gives an accuracy figure or a confidence display for suggestions.

What the design takes from this:
- Rules sit above the model.
- The model never overwrites a person's code.
- Only empty fields are suggested.
- Every code records its source.
- A person reviews every suggestion.

The open question the project adds is when a suggestion is safe enough to approve quickly, and how a company would know. Nothing here describes any platform's internal systems.

## Data research

The goal was data where each organization codes transactions to its own chart of accounts, with merchant text, amount and date. No private-company ledgers are public, so the search covered public spending data:

- **US open payment registers** (Socrata portals): Connecticut state and quasi-public agencies, Los Angeles City, Ramsey County and Fulton County. Each has vendor, amount, date and the organization's own expense account, and some have department and description.
- **UK council purchase-card files** (data.gov.uk transparency releases). These are the closest match to business card spend: merchant descriptors, merchant category codes, service areas and the council's expense code. Cambridgeshire, Calderdale and Barnet had long, consistent files.
- **Public bank-transaction and receipt datasets.** These are mostly consumer data with generic categories and no company chart of accounts, so they were not used for evaluation.

Every source was mapped to one record format (`data_prep/standardize.py`). Missing fields stay empty, and nothing is invented.

## What was tried, and what it showed

1. **Lookup and ranker baselines.** History alone, meaning the merchant's usual account, already gets most consistent merchants right. The remaining problem is new merchants and mixed history.
2. **Simulated data.**
   - A pilot compared three generators: hand-written code, LLM-written companies, and a hybrid.
   - A model trained only on simulated rows scored 2.0% on a real council, against 24.4% with the same number of real rows.
   - So simulated data is not used to measure anything. Generated companies are used only to teach next steps, which real data has no labels for.
3. **Cross-company models without history** did not transfer to new organizations. The project then focused on learning from each company's own history.
4. **Fine-tuning a 4B decision model** on retrieved history.
   - Adding generated next-step data raised next-step agreement from 62% to about 80%.
   - Account accuracy stayed flat across data mixes, including three times more account rows. Differences of 2–3 points were within seed noise.
5. **Label quality for next steps.** Two LLM labellers on the same 100 rows agreed 85% of the time, but differed sharply on "ask the spender" (11 times against 0). That class has no reliable ground truth in public data.
6. **A shortcut in generated data.** Generated "ask the spender" rows usually carried a cardholder name, and real rows never do. The model learned the shortcut. Hiding the cardholder on most generated rows, and adding real rows paid to people, fixed it.
7. **Error analysis on development, then on test.** Most errors come from inconsistent coding or missing information. Too-confident "approve" decisions on low-confidence accounts led to the combined safe-to-approve rule ([0008](decisions/0008-safe-to-approve.md)).
8. **Rolling history.** Reading errors one by one showed history frozen months before the transaction. Switching to rolling history raised development accuracy by about 10 points ([0007](decisions/0007-rolling-history.md)).
9. **Expert review.** Separate reviews were done from a product, an evaluation, an ML infrastructure and a bookkeeping point of view. They led to:
   - the vendor-rule baseline
   - confidence intervals
   - per-company calibration
   - value-weighted errors and merchant normalization as next steps

## Prior work

Transaction categorization is a well-studied problem, mostly for consumer banking with fixed categories. Decision models that score options supplied in the prompt are prior work: the Unsloth decision-model head and Jev-style typed decisions. Retrieval of similar past examples into the prompt is standard practice. The contribution here is the evaluation setup and the product framing, not a new method.
