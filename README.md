# Transaction coding with company history

Suggests an account for each business card or bank transaction, from the company's own chart of accounts. A person approves every suggestion. The system makes that quick, and says when it is unsure and what would settle it.

It is built and tested on real public spending records, replaying each public body as if it were a customer.

## Result

On organizations never used in training, compared with the rule a bookkeeper would write (*this merchant goes to its usual account*):

| | Development (5 organizations) | Test (2 UK councils) |
|---|---|---|
| Vendor rule | 65.3% | 49.8% |
| **Model** | **71.9%** | **59.2%** |
| Model, right account in top 5 | 87.6% | 87.5% |

The percentages are how often the first suggestion is right.

- The model wins on **new merchants** and on **merchants coded several ways**. For consistent merchants, a rule is as good, so rules run first.
- Most remaining errors come from **inconsistent coding or missing information**, not the model. For those it suggests a next step instead of guessing: request a receipt, ask the spender, look up the merchant, or send to a bookkeeper.

**Review time per 1,000 transactions,** estimated from stated assumptions:

| | No suggestions | Vendor rules | Model |
|---|---|---|---|
| Development | 8–17 h | 3–7 h | **2–4 h** |
| Test | 8–17 h | 5–9 h | **2–4 h** |

With the app's safe-to-approve rule, 40% of development transactions are marked safe to skim, and 0.5% of those are wrong. On the test councils it is 21% and 8.2%, so confidence needs calibrating per company first ([write-up](docs/writeup.md#business-result)).


## How it works

1. A company rule matches the merchant, and the model is not asked. Otherwise:
2. Retrieve up to 20 earlier transactions of the same company that are most similar, using only history before that date.
3. A fine-tuned Qwen3-4B reads the transaction, the history and the company's accounts. It gives a probability for each account and each next step.
4. If the next step is "approve" and confidence is at least 0.9, the suggestion is marked safe to approve.

## Read more

- [Write-up](docs/writeup.md): the full results, evaluation, error analysis, data and limits. It's a five-minute read.
- [Design decisions](docs/decisions/): why it is built this way.
- [Research notes](docs/research.md): product and data research, and what each experiment showed.
- [Demo](demo/README.md): a local review app.

## Repository

| Folder | Contents |
|---|---|
| `data_prep/` | Download and standardize the public data |
| `src/` | Build training and evaluation rows, train, score, baselines, error analysis |
| `labels/` | Next-step labelling rubric and labels |
| `results/` | Split, test protocol, predictions, error analyses |
| `demo/` | Local review app, plus an inference server for a GPU |

Data and model weights are not included; `data_prep/` and `src/` rebuild them. Scripts run from the repository root with `python src/<script>.py`. The analysis scripts need only the standard library; `uv sync --extra demo` installs the demo, and `--extra gpu` the training stack. Code is under the MIT licence.
