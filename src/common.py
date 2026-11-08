"""Shared pieces: loading an organization's records, retrieving similar past transactions, the prompt, and the two questions."""
import collections, gzip, json, re

slug = lambda o: re.sub(r"[^a-zA-Z0-9]+", "_", o)[:60]

# Next steps and their definitions, as shown to the model.
ACTIONS = {'accept': 'The evidence settles one account',
           'request_document': 'A receipt or invoice showing the item would settle it',
           'ask_person': 'Only the person who spent it knows the purpose or beneficiary',
           'lookup_merchant': "The merchant's business is unknown", 'send_to_bookkeeper': 'It needs accounting judgment, or the risk is high'}


def load(org):
    """All standardized records of one organization, in date order."""
    return sorted((json.loads(l) for l in gzip.open(f"data/std/{slug(org)}.jsonl.gz", "rt")), key=lambda r: r["date"])


def read(path):
    return [json.loads(l) for l in gzip.open(path, "rt")]


def write(path, rows):
    with gzip.open(path, "wt") as f:
        for x in rows:
            f.write(json.dumps(x) + "\n")


def retrieve(past, r, k=20):
    """Up to k past transactions, ranked by exact matches on merchant, merchant category and department, newest first; at most 8 per account."""
    def rank(p):
        m = p["merchant_name"].lower() == r["merchant_name"].lower(); d = bool(r["department"]) and p["department"] == r["department"]; c = bool(r["merchant_category"]) and p["merchant_category"] == r["merchant_category"]
        return (m and d, m, c and d, c, d)
    scored = sorted((p for p in past if any(rank(p))), key=lambda p: (rank(p), p["date"]), reverse=True); picked, per = [], collections.Counter()
    for p in scored:
        if per[p["account"]] < 8:
            picked.append(p); per[p["account"]] += 1
        if len(picked) == k:
            break
    return picked


def prompt(r, shown):
    lines = "\n".join(f"{p['merchant_name']} | {p['amount']} | {p['department']} | {p['merchant_category']} | {p['memo']} -> {p['account']}" for p in shown) or "None available."
    return f"New transaction: merchant={r['merchant_name']}; amount={r['amount']} {r['currency']}; date={r['date']}; department={r['department']}; merchant category={r['merchant_category']}; memo={r['memo']}.\n\nSimilar past transactions at this organization:\n{lines}"


def questions(options, with_action=True):
    q = {"account": {"type": "choice", "instructions": "Which account should the new transaction be coded to?", "criteria": {o: o for o in options}}}
    if with_action:
        q["action"] = {"type": "choice", "instructions": "What is the cheapest next step likely to settle the account?", "criteria": ACTIONS}
    return q
