"""Vendor-rule baseline: 'this merchant -> its usual account', learned from the organization's history before each row.
Exact merchant text, case-insensitive. Rows without a rule get no suggestion."""
import collections, gzip, json, re
from common import slug
SETS = {"development": ("gen/eval/dev.jsonl.gz", "results/development/fixed_history/seed1/dev.json", "results/development/rolling.json"),
        "test": ("gen/eval/test.jsonl.gz", None, "results/test/rolling.json")}
RULES = {"any history (majority account)": (1, 0.0), "strict (3+ uses, 80%+ one account)": (3, 0.8)}
for sname, (rows_path, frozen_p, rolling_p) in SETS.items():
    rows = [json.loads(l) for l in gzip.open(rows_path, "rt")]; D = {}
    for o in {r["org"] for r in rows}:
        D[o] = sorted((json.loads(l) for l in gzip.open(f"data/std/{slug(o)}.jsonl.gz", "rt")), key=lambda r: r["date"])
    for hist, model_p in (("frozen", frozen_p), ("rolling", rolling_p)):
        if model_p is None:
            continue
        M = json.load(open(model_p)); assert [(x["org"], x["i"]) for x in M] == [(r["org"], r["i"]) for r in rows]
        print(f"\n== {sname}, {hist} history ({len(rows)} rows). Model top-1 on all rows: {100*sum(x['codes'][0]==x['label'] for x in M)/len(rows):.1f}%")
        for rname, (min_n, min_share) in RULES.items():
            fired = right = model_right = 0
            for r, x in zip(rows, M):
                d = D[r["org"]]; past = d[:1000] if hist == "frozen" else d[:r["i"]]; m = d[r["i"]]["merchant_name"].lower()
                c = collections.Counter(p["account"] for p in past if p["merchant_name"].lower() == m)
                if not c: continue
                acc, k = c.most_common(1)[0]; n = sum(c.values())
                if n < min_n or k / n < min_share: continue
                fired += 1; right += acc == r["label"]; model_right += x["codes"][0] == r["label"]
            print(f"  rule {rname:38} fires on {100*fired/len(rows):4.1f}% of rows | right when it fires {100*right/max(1,fired):5.1f}% (model on same rows {100*model_right/max(1,fired):5.1f}%) | top-1 over all rows {100*right/len(rows):5.1f}%")
