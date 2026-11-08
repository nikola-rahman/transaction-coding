"""Fix one set of test rows for every method."""
import gzip, json, random, re
from common import slug
split = json.load(open("results/split.json")); out = {}
for org in split["validation"]:
    n_rows = sum(1 for _ in gzip.open(f"data/std/{slug(org)}.jsonl.gz", "rt")); out[org] = {}
    for n in (200, 1000, 5000):
        pool = list(range(n, min(n + 2000, n_rows)))
        if len(pool) >= 500:
            out[org][str(n)] = sorted(random.Random(f"{org}{n}").sample(pool, 200))
json.dump(out, open("results/eval_rows.json", "w"))
print({k: list(v) for k, v in out.items()})
