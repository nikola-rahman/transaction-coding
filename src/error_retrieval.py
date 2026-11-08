"""Was the true account available in the 1,000-row past, and did retrieval show it? Uses the same fixed validation rows."""
import collections, gzip, json, re
from common import slug
rows = [json.loads(l) for l in gzip.open("gen/eval/dev.jsonl.gz", "rt")]; A = json.load(open("results/development/fixed_history/seed1/dev.json")); B = json.load(open("results/development/fixed_history/seed2/dev.json"))
cache = {}; C = collections.Counter(); H = collections.Counter(); H5 = collections.Counter()
for r, a, b in zip(rows, A, B):
    o = r["org"]
    if o not in cache:
        cache[o] = sorted((json.loads(l) for l in gzip.open(f"data/std/{slug(o)}.jsonl.gz", "rt")), key=lambda x: x["date"])
    d = cache[o]; t = d[a["i"]]; assert t["account"] == r["label"]; past = d[:1000]; acc = {p["account"] for p in past}; shown = r["label"] in r["state"].split("Similar past")[1]; same = [p for p in past if p["merchant_name"].lower() == t["merchant_name"].lower()]
    k = "shown" if shown else "merchant_past_has_label_not_shown" if any(p["account"] == r["label"] for p in same) else "account_in_past_not_via_merchant" if r["label"] in acc else "account_never_used_in_past"
    C[k] += 1; H[k] += (a["codes"][0] == r["label"]) + (b["codes"][0] == r["label"]); H5[k] += (r["label"] in a["codes"]) + (r["label"] in b["codes"])
for k, v in C.most_common():
    print(f"{k:38} {v:4} top1 {100*H[k]/(2*v):5.1f} top5 {100*H5[k]/(2*v):5.1f}")
