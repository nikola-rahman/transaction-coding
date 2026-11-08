"""Rows paid to people, chosen by code from merchant text only. Training organizations go to training batches, action-evaluation organizations to a held batch. The recorded account is never shown."""
import collections, gzip, json, random, re
from common import load, prompt, retrieve, slug

split = json.load(open("results/split.json")); rng = random.Random(20261113); OUT = "labels"
HOLD = {"ct:Connecticut Innovations", "ct:Materials Innovation and Recycling Authority"}
BIZ = re.compile(r"\b(inc|llc|llp|ltd|co|corp|company|group|services?|assoc\w*|bank|city|town|state|county|university|college|school|center|centre|hospital|consult\w*|systems?|solutions|partners|foundation|trust|fund|insurance|authority|dept|department|of|the|and|for|gas|energy|electric|water|supply|hotel|inn|bar|grill|restaurant|cafe|pizza|law|office|american|national|first|united|north|south|east|west|new)\b", re.I)


def person(name):
    n = name.strip()
    if not n or BIZ.search(n) or re.search(r"[\d&/*#]", n):
        return False
    return bool(re.fullmatch(r"[A-Za-z'\-]+,\s?[A-Za-z'\-]+(\s[A-Za-z.]+)?", n) or re.fullmatch(r"[A-Z][a-z'\-]+(\s[A-Z]\.?)*\s[A-Z][a-z'\-]+", n) or re.fullmatch(r"[A-Z][A-Z'\-]+\s[A-Z]\.?\s?[A-Z][A-Z'\-]+", n))






pool = {True: [], False: []}; counts = collections.Counter()
for org in split["train"]:
    rows = load(org); idx = [i for i, r in enumerate(rows) if i >= 50 and person(r["merchant_name"])]; counts[org] = len(idx); rng.shuffle(idx); seen = collections.Counter()
    for t in idx:
        r = rows[t]
        if seen[r["merchant_name"].lower()] >= 2:
            continue
        seen[r["merchant_name"].lower()] += 1
        H = min(rng.choice([200, 500, 1000, 2000]), t); past = rows[t - H:t]; same = [p for p in past if p["merchant_name"].lower() == r["merchant_name"].lower()]
        pool[org in HOLD].append({"org": org, "row": r, "history": retrieve(past, r), "chart": sorted({p["account"] for p in rows[max(0, t - H):t + 2000]}), "uses": len(same)})
        if seen.total() >= 80:
            break
print(counts.most_common(), {k: len(v) for k, v in pool.items()})
rng.shuffle(pool[False]); rng.shuffle(pool[True]); picked = [(x, False) for x in pool[False][:300]] + [(x, True) for x in pool[True][:100]]; meta = []
for n, (x, held) in enumerate(picked):
    x["id"] = f"p{n:04d}"; meta.append({"id": x["id"], "org": x["org"], "held_out": held, "case": "person_payee", "recorded": x["row"]["account"]})
json.dump(meta, open(f"{OUT}/real3_meta.json", "w"), indent=0)
for b in range((len(picked) + 99) // 100):
    with open(f"{OUT}/batches/real3_{b:02d}.jsonl", "w") as f:
        for x, _ in picked[b * 100:(b + 1) * 100]:
            r = x["row"]; hist = [{"merchant": p["merchant_name"], "amount": p["amount"], "department": p["department"], "merchant_category": p["merchant_category"], "memo": p["memo"], "account": p["account"]} for p in x["history"]]
            f.write(json.dumps({"id": x["id"], "transaction": {"merchant": r["merchant_name"], "amount": r["amount"], "currency": r["currency"], "date": r["date"], "payment_kind": r["payment_kind"], "department": r["department"], "merchant_category": r["merchant_category"], "memo": r["memo"]}, "account_count": len(x["chart"]), "accounts_sample": rng.sample(x["chart"], min(30, len(x["chart"]))), "past_transactions": hist, "past_uses_of_merchant": x["uses"]}) + "\n")
print(len(picked), collections.Counter(m["org"] for m in meta), sum(m["held_out"] for m in meta))
for x, _ in rng.sample(picked, 12):
    print(x["row"]["merchant_name"], x["row"]["amount"], x["row"]["account"])
