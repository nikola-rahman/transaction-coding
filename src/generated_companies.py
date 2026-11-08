"""Turn subagent-written companies into transaction histories. Code does all sampling; action labels follow the rubric from what evidence is present."""
import collections, glob, gzip, json, math, os, random, re
rng = random.Random(20261108); HOLD = {"c13", "c14", "c15"}; ROWS, PER = 1800, 450


def date(i, n):
    day = int(365 * i / n); m = day // 31 + 1; return f"2026-{min(m, 12):02d}-{day % 28 + 1:02d}"


def mess(name, kind):
    if kind != "card" or rng.random() < 0.55:
        return name
    s = name.upper()
    return rng.choice([f"SQ *{s}"[:22], f"TST* {s}"[:22], f"{s} {rng.randint(1000, 99999)}"[:22], f"PAYPAL *{s.replace(' ', '')}"[:22], s[:18]])


def retrieve(past, r, k=20):
    def rank(p):
        m = p["key"] == r["key"]; d = p["department"] == r["department"]; c = p["merchant_category"] == r["merchant_category"]
        return (m and d, m, c and d, c, d)
    scored = sorted((p for p in past if any(rank(p))), key=lambda p: (rank(p), p["i"]), reverse=True); picked, per = [], collections.Counter()
    for p in scored:
        if per[p["account"]] < 8:
            picked.append(p); per[p["account"]] += 1
        if len(picked) == k:
            break
    return picked


def state(r, shown):
    lines = "\n".join(f"{p['merchant_name']} | {p['amount']} | {p['department']} | {p['merchant_category']} | {p['memo']} -> {p['account']}" for p in shown) or "None available."
    return f"New transaction: merchant={r['merchant_name']}; amount={r['amount']} USD; date={r['date']}; department={r['department']}; merchant category={r['merchant_category']}; memo={r['memo']}; card={r['card']}; receipt={r['receipt']}.\n\nSimilar past transactions at this organization:\n{lines}"


def action(r, past):
    same = [p for p in past if p["key"] == r["key"]]; accounts = {p["account"] for p in same}; p = r["p"]; multi = len(r["m"]["purposes"]) > 1
    resolved = r["memo"] is not None or r["receipt"] is not None
    big = bool(past) and r["amount"] >= sorted(x["amount"] for x in past)[int(len(past) * 0.97)]
    unusual = bool(same) and r["amount"] > 1.5 * max(x["amount"] for x in same)
    if p["decided_by"] == "accounting_judgment" or (big and not resolved and (multi or len(same) < 3)):
        return "send_to_bookkeeper", "accounting_judgment"
    if multi and not resolved:
        return ("ask_person", "purpose") if p["decided_by"] == "purpose" else ("request_document", "item")
    if not same and not r["m"].get("clear_name", True) and not resolved:
        return "lookup_merchant", "merchant"
    if unusual and not resolved:
        return "request_document", "item"
    return "accept", "nothing"


out = {"train": [], "held": []}; stats = collections.Counter(); bad = 0; boost = []; rng2 = random.Random(20261112)
for path in sorted(glob.glob("labels/companies/c*.json")):
    cid = os.path.basename(path)[:3]; c = json.load(open(path)); chart = c["chart"]; rows = []
    merchants = []
    for m in c["merchants"]:
        ps = [p for p in m.get("purposes", []) if p.get("account") in chart]; bad += len(m.get("purposes", [])) - len(ps)
        if ps:
            merchants.append({**m, "purposes": ps})
    weights = [rng.paretovariate(1.1) for _ in merchants]; people = c["people"]
    for i in range(ROWS):
        m = rng.choices(merchants, weights)[0]; p = rng.choices(m["purposes"], [max(float(x.get("weight", 1)), .01) for x in m["purposes"]])[0]; person = rng.choice(people)
        lo, hi = max(float(p.get("amount_low", 5)), .5), max(float(p.get("amount_high", 50)), 1); amt = round(math.exp(rng.uniform(math.log(lo), math.log(max(hi, lo * 1.01)))), 2)
        kind = m.get("payment_kind", "card"); memo = p.get("memo") if rng.random() < 0.3 else None; receipt = p.get("item_shown_by_document") if rng.random() < 0.25 else None
        rows.append({"i": i, "key": m["name"].lower(), "merchant_name": mess(m["name"], kind), "amount": amt, "date": date(i, ROWS), "department": person.get("department"), "merchant_category": m.get("merchant_category"), "memo": memo, "receipt": receipt, "card": person.get("card_name") if kind == "card" else None, "account": p["account"], "m": m, "p": p})
    pick = rng.sample(range(60, ROWS), PER)
    for t in pick:
        r = rows[t]; H = rng.choice([50, 200, 500, 1000]); past = rows[max(0, t - H):t]; a, u = action(r, past); shown = retrieve(past, r)
        size = min(len(chart), rng.randint(30, 90)); others = [x for x in chart if x != r["account"]]; options = rng.sample(others, min(size, len(others))) + [r["account"]]; rng.shuffle(options)
        side = "held" if cid in HOLD else "train"; out[side].append({"org": "gen:" + cid, "state": state(r, shown), "options": options, "label": r["account"], "action": a, "unknown": u}); stats[(side, a)] += 1
    if cid not in HOLD:  # rare class: unfamiliar merchants, from short histories; separate random stream keeps the held rows fixed
        found = []
        for t in range(60, ROWS):
            r = rows[t]; past = rows[max(0, t - rng2.choice([50, 100, 200])):t]; a, u = action(r, past)
            if a == "lookup_merchant":
                found.append((r, past, a, u))
        for r, past, a, u in rng2.sample(found, min(60, len(found))):
            others = [x for x in chart if x != r["account"]]; options = rng2.sample(others, min(rng2.randint(30, 90), len(others))) + [r["account"]]; rng2.shuffle(options)
            boost.append({"org": "gen:" + cid, "state": state(r, retrieve(past, r)), "options": options, "label": r["account"], "action": a, "unknown": u})
with gzip.open("gen/boost.jsonl.gz", "wt") as f:
    for x in boost:
        f.write(json.dumps(x) + "\n")
print("boost", len(boost), len({x["org"] for x in boost}))
for side, data in out.items():
    rng.shuffle(data)
    with gzip.open(f"gen/{side}.jsonl.gz", "wt") as f:
        for x in data:
            f.write(json.dumps(x) + "\n")
print({k: len(v) for k, v in out.items()}, sorted(stats.items()), "dropped purposes", bad)
