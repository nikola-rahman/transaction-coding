"""Add person-payee labels: person-payee labels join training; the held batch keeps both labellers; card is hidden on most generated rows because real rows never carry it and the action rule never uses it."""
import collections, glob, gzip, json, random, re
rng = random.Random(20261114); rd = lambda p: [json.loads(l) for l in gzip.open(p, "rt")]


def wr(name, data):
    with gzip.open(f"gen/training/{name}.jsonl.gz", "wt") as f:
        for x in data:
            f.write(json.dumps(x) + "\n")
    print(name, len(data), collections.Counter(x.get("action") for x in data).most_common())


import os; os.makedirs("gen/training", exist_ok=True)
meta = {m["id"]: m for m in json.load(open("labels/real3_meta.json"))}; A, B = {}, {}
for f in glob.glob("labels/out/real3_*_A.jsonl"):
    for l in open(f):
        d = json.loads(l); A[d["id"]] = d
for l in open("labels/out/real3_03_B.jsonl"):
    d = json.loads(l); B[d["id"]] = d
tr, held = [], []
for f in sorted(glob.glob("labels/batches/real3_*.jsonl")):
    for l in open(f):
        x = json.loads(l); t = x["transaction"]; m = meta[x["id"]]; lab = A[x["id"]]
        lines = "\n".join(f"{p['merchant']} | {p['amount']} | {p['department']} | {p['merchant_category']} | {p['memo']} -> {p['account']}" for p in x["past_transactions"]) or "None available."
        s = f"New transaction: merchant={t['merchant']}; amount={t['amount']} {t['currency']}; date={t['date']}; department={t['department']}; merchant category={t['merchant_category']}; memo={t['memo']}; card=None; receipt=None.\n\nSimilar past transactions at this organization:\n{lines}"
        r = {"org": m["org"], "case": "person_payee", "state": s, "options": sorted(set(x["accounts_sample"]) | {m["recorded"]}), "label": m["recorded"], "action": lab["action"], "unknown": lab["unknown"]}
        if m["held_out"]:
            r["action_b"] = B[x["id"]]["action"]; held.append(r)
        else:
            tr.append(r)
v2 = rd("gen/training/ra_train.jsonl.gz"); seen = {r["state"] for r in rd("gen/training/ra_held.jsonl.gz") + rd("gen/training/ra_hard_held.jsonl.gz") + held}
keep = [r for r in v2 + tr if r["state"] not in seen]; print("dropped for matching held", len(v2) + len(tr) - len(keep)); wr("ra3_train", keep); wr("ra_person_held", held)
g = rd("gen/training/gen_bal.jsonl.gz"); masked = 0
for r in g:
    if rng.random() < 0.8:
        r["state"], n = re.subn(r"; card=[^;]*; receipt=", "; card=None; receipt=", r["state"], count=1); masked += n
print("masked", masked); wr("gen_mask", g)
