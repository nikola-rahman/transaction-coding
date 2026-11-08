"""Code-only sampling for action labels. Training organizations only, fixed seed, balanced by case type and amount."""
import collections, gzip, json, os, random, re
from common import load, prompt, retrieve, slug

split = json.load(open("results/split.json")); rng = random.Random(20261106); OUT = "labels"; os.makedirs(f"{OUT}/batches", exist_ok=True)
HOLD = {"ct:Connecticut Innovations", "ct:Materials Innovation and Recycling Authority"}  # held out for action evaluation






pool = []
for org in split["train"]:
    rows = load(org); share = 160 if len(rows) > 100000 else 70
    for _ in range(share * 3):
        H = min(rng.choice([200, 500, 1000, 2000]), max(50, len(rows) // 2)); s = rng.randint(0, max(0, len(rows) - H - 1))
        if s + H >= len(rows):
            continue
        t = rng.randint(s + H, min(len(rows) - 1, s + H + 2000)); r = rows[t]; past = rows[s:s + H]; same = [p for p in past if p["merchant_name"].lower() == r["merchant_name"].lower()]; accounts = {p["account"] for p in same}
        case = "new_merchant" if not same else "several_accounts" if len(accounts) > 1 else "thin_history" if len(same) < 3 else "easy"
        amounts = sorted(p["amount"] for p in past); big = amounts and r["amount"] >= amounts[int(len(amounts) * 0.95)]
        chart = sorted({p["account"] for p in rows[s:s + H + 2000]})
        pool.append({"org": org, "case": case, "large": bool(big), "row": r, "history": retrieve(past, r), "chart": chart, "uses": len(same)})
rng.shuffle(pool); want = collections.Counter(); picked = []
for x in pool:
    key = (x["org"] in HOLD, x["case"], x["large"]); limit = 110 if x["large"] else 190
    if want[key] < limit:
        want[key] += 1; picked.append(x)
rng.shuffle(picked); picked = picked[:1000]
meta = []
for n, x in enumerate(picked):
    x["id"] = f"r{n:04d}"; meta.append({"id": x["id"], "org": x["org"], "case": x["case"], "large": x["large"], "held_out": x["org"] in HOLD, "recorded": x["row"]["account"]})
json.dump(meta, open(f"{OUT}/real_meta.json", "w"), indent=0)
for b in range(10):
    part = picked[b * 100:(b + 1) * 100]
    with open(f"{OUT}/batches/real_{b:02d}.jsonl", "w") as f:
        for x in part:
            r = x["row"]; hist = [{"merchant": p["merchant_name"], "amount": p["amount"], "department": p["department"], "merchant_category": p["merchant_category"], "memo": p["memo"], "account": p["account"]} for p in x["history"]]
            f.write(json.dumps({"id": x["id"], "transaction": {"merchant": r["merchant_name"], "amount": r["amount"], "currency": r["currency"], "date": r["date"], "payment_kind": r["payment_kind"], "department": r["department"], "merchant_category": r["merchant_category"], "memo": r["memo"]}, "account_count": len(x["chart"]), "accounts_sample": rng.sample(x["chart"], min(30, len(x["chart"]))), "past_transactions": hist, "past_uses_of_merchant": x["uses"]}) + "\n")
print(len(picked), collections.Counter((m["case"], m["large"]) for m in meta), sum(m["held_out"] for m in meta))
