"""Account rows with retrieved history: training rows from training organizations, and the fixed development rows (gen/eval/dev) every method is scored on."""
import collections, gzip, json, random, re
from common import load, prompt, retrieve, slug

split = json.load(open("results/split.json")); EVAL = json.load(open("results/eval_rows.json")); rng = random.Random(0)








train = []
for org in split["train"]:
    rows = load(org); take = 1300 if len(rows) > 100000 else 300
    for _ in range(take):
        H = rng.choice([200, 500, 1000, 2000]); H = min(H, max(50, len(rows) // 2)); s = rng.randint(0, max(0, len(rows) - H - 1)); past = rows[s:s + H]
        if s + H >= len(rows):
            continue
        t = rng.randint(s + H, min(len(rows) - 1, s + H + 2000)); r = rows[t]; chart = sorted({p["account"] for p in rows[s:s + H + 2000]})
        size = rng.randint(30, 250); others = [a for a in chart if a != r["account"]]; options = rng.sample(others, min(size, len(others))) + [r["account"]]; rng.shuffle(options)
        train.append({"org": org, "state": prompt(r, retrieve(past, r)), "options": options, "label": r["account"]})
rng.shuffle(train)
with gzip.open("gen/accounts/train.jsonl.gz", "wt") as f:
    for x in train:
        f.write(json.dumps(x) + "\n")
val, test = [], []
for org, levels in EVAL.items():
    rows = load(org); past = rows[:1000]; counts = collections.Counter(r["account"] for r in past); chart = [a for a, _ in counts.most_common()] + sorted({r["account"] for r in rows[:3000]} - set(counts)); blocked = set(levels["1000"])
    for i in levels["1000"]:
        sh = retrieve(past, rows[i]); test.append({"org": org, "i": i, "state": prompt(rows[i], sh), "label": rows[i]["account"], "options": list(dict.fromkeys([p["account"] for p in sh] + chart))[:255]})
    for i in random.Random(org).sample([i for i in range(1000, min(3000, len(rows))) if i not in blocked], 20):
        sh = retrieve(past, rows[i]); val.append({"org": org, "state": prompt(rows[i], sh), "label": rows[i]["account"], "options": list(dict.fromkeys([p["account"] for p in sh] + chart))[:255]})
import os; os.makedirs("gen/eval", exist_ok=True)
for path, data in (("gen/accounts/monitor.jsonl.gz", val), ("gen/eval/dev.jsonl.gz", test)):
    with gzip.open(path, "wt") as f:
        for x in data:
            f.write(json.dumps(x) + "\n")
print(len(train), len(val), len(test), collections.Counter(x["org"].split(":")[0] for x in train))
