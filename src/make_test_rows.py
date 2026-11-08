"""Test rows for the two held-out councils, built exactly like the development rows in make_account_rows.py."""
import collections, gzip, json, random, re, sys
from common import load, prompt, retrieve, slug
split = json.load(open("results/split.json")); out = []
for org in split["sealed_test"]:
    rows = load(org); pool = list(range(1000, min(3000, len(rows)))); idx = sorted(random.Random(f"{org}1000").sample(pool, 200))
    past = rows[:1000]; counts = collections.Counter(r["account"] for r in past); chart = [a for a, _ in counts.most_common()] + sorted({r["account"] for r in rows[:3000]} - set(counts))
    for i in idx:
        sh = retrieve(past, rows[i]); out.append({"org": org, "i": i, "state": prompt(rows[i], sh), "label": rows[i]["account"], "options": list(dict.fromkeys([p["account"] for p in sh] + chart))[:255]})
with gzip.open("gen/eval/test.jsonl.gz", "wt") as f:
    for x in out: f.write(json.dumps(x) + "\n")
print(len(out), collections.Counter(x["org"] for x in out), "label in options", sum(x["label"] in x["options"] for x in out), "max options", max(len(x["options"]) for x in out))
