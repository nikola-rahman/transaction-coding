"""Training data. Account rows exclude the action-evaluation organizations; hard labels join training or a separate held set; generated rows get a capped-accept version."""
import collections, gzip, importlib.util, json, glob, random, re
from common import load, prompt, retrieve, slug
HOLD = {"ct:Connecticut Innovations", "ct:Materials Innovation and Recycling Authority"}

split = json.load(open("results/split.json")); rng = random.Random(20261111)
rd = lambda p: [json.loads(l) for l in gzip.open(p, "rt")]


def wr(name, data):
    with gzip.open(f"gen/training/{name}.jsonl.gz", "wt") as f:
        for x in data:
            f.write(json.dumps(x) + "\n")
    print(name, len(data), collections.Counter(x.get("action") for x in data).most_common())








import os; os.makedirs("gen/training", exist_ok=True)
base = [r for r in rd("gen/accounts/train.jsonl.gz") if r["org"] not in HOLD]; wr("train_base", base)
more = list(base)
for org in split["train"]:
    if org in HOLD:
        continue
    rows = load(org); take = 2700 if len(rows) > 100000 else 700
    for _ in range(take):
        H = min(rng.choice([200, 500, 1000, 2000]), max(50, len(rows) // 2)); s = rng.randint(0, max(0, len(rows) - H - 1)); past = rows[s:s + H]
        if s + H >= len(rows):
            continue
        t = rng.randint(s + H, min(len(rows) - 1, s + H + 2000)); r = rows[t]; chart = sorted({p["account"] for p in rows[s:s + H + 2000]})
        size = rng.randint(30, 250); others = [a for a in chart if a != r["account"]]; options = rng.sample(others, min(size, len(others))) + [r["account"]]; rng.shuffle(options)
        more.append({"org": org, "state": prompt(r, retrieve(past, r)), "options": options, "label": r["account"]})
rng.shuffle(more); wr("train_more", more)
meta = {m["id"]: m for m in json.load(open("labels/real2_meta.json"))}; L = {}
for f in glob.glob("labels/out/real2_*_A.jsonl"):
    for l in open(f):
        d = json.loads(l); L[d["id"]] = d
tr, held = [], []
for f in sorted(glob.glob("labels/batches/real2_*.jsonl")):
    for l in open(f):
        x = json.loads(l); t = x["transaction"]; m = meta[x["id"]]; lab = L[x["id"]]
        lines = "\n".join(f"{p['merchant']} | {p['amount']} | {p['department']} | {p['merchant_category']} | {p['memo']} -> {p['account']}" for p in x["past_transactions"]) or "None available."
        s = f"New transaction: merchant={t['merchant']}; amount={t['amount']} {t['currency']}; date={t['date']}; department={t['department']}; merchant category={t['merchant_category']}; memo={t['memo']}; card=None; receipt=None.\n\nSimilar past transactions at this organization:\n{lines}"
        (held if m["held_out"] else tr).append({"org": m["org"], "case": m["case"], "state": s, "options": sorted(set(x["accounts_sample"]) | {m["recorded"]}), "label": m["recorded"], "action": lab["action"], "unknown": lab["unknown"]})
old_tr, old_held = rd("gen/real_actions_train.jsonl.gz"), rd("gen/real_actions_held.jsonl.gz")
assert not {r["org"] for r in old_tr + tr} & HOLD and {r["org"] for r in old_held + held} <= HOLD
seen = {r["state"] for r in old_held + held}; print("train rows matching a held state", sum(r["state"] in seen for r in old_tr + tr))
keep = [r for r in old_tr + tr if r["state"] not in seen]; wr("ra_train", keep); wr("ra_hard_held", held)
wr("ra_train_old", old_tr); wr("ra_held", old_held)
g = rd("gen/train.jsonl.gz"); wr("gen_full", g)
acc = [r for r in g if r["action"] == "accept"]; rest = [r for r in g if r["action"] != "accept"]; rng.shuffle(acc); boost = rd("gen/boost.jsonl.gz"); bal = acc[:len(rest)] + rest + boost; rng.shuffle(bal); wr("gen_bal", bal)
wr("gen_old", rd("gen/train_16.jsonl.gz")); wr("gen_held", rd("gen/held.jsonl.gz"))
wr("monitor", rd("gen/accounts/monitor.jsonl.gz")); wr("dev", rd("gen/eval/dev.jsonl.gz"))
