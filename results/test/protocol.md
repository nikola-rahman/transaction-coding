# Test set

The test set is two UK councils, Calderdale and Barnet, held out of training and development.

## Rows

- 200 transactions per council, sampled from transactions 1,000 to 2,999 in date order with seed `f"{org}1000"` (`src/make_test_rows.py`).
- Rolling history: each row sees every transaction the council recorded before it (`src/make_rolling_rows.py`).
- Options are the accounts in the retrieved history, then the council's other accounts, capped at 255.

## Model and scoring

- Model: the trained adapter (seed 1), Qwen3-4B base, as chosen on development.
- Questions: account and next step, as defined in `src/common.py`.
- Scoring: `src/score.py`. Before scoring, it re-scores 20 development rows and checks that they match the training run.
- Safe-to-approve threshold: 0.9, chosen on development.

## Results

`rolling.json`:
- First suggestion right: 59.2%.
- Right account in the top 5: 87.5%.
