"""One record format for all sources, plus a whole-organization split. Values are never invented."""
import collections, glob, gzip, json, os, re

OUT = "data/std"; os.makedirs(OUT, exist_ok=True)
VALIDATION = {"fulton", "ct:Connecticut Green Bank", "ct:CT Lottery", "ct:Connecticut Airport Authority", "council:cambridgeshire"}
SEALED = {"council:calderdale", "council:barnet"}


def record(org, source, kind, currency, r):
    return {"organization": org, "source": source, "payment_kind": kind, "merchant_name": r["merchant"], "amount": r["amount"], "currency": currency, "date": r["date"],
            "department": r.get("area") or None, "memo": r.get("memo") or None, "merchant_category": r.get("merchant_category") or None, "account": r["label"]}


split = collections.defaultdict(dict)
def save(org, rows):
    part = "sealed_test" if org in SEALED else "validation" if org in VALIDATION else "train"
    with gzip.open(f"{OUT}/{re.sub(r'[^a-zA-Z0-9]+', '_', org)[:60]}.jsonl.gz", "wt") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    split[part][org] = {"rows": len(rows), "accounts": len({r["account"] for r in rows})}


for path in sorted(glob.glob("data/clean/*.jsonl.gz")):
    rows = [json.loads(l) for l in gzip.open(path, "rt")]
    org = rows[0]["org"]
    save(org, [record(org, "us_public_payments", "bank_payment", "USD", r) for r in rows])
for name in ("cambridgeshire", "calderdale", "barnet"):
    org = f"council:{name}"; rows = [json.loads(l) for l in open(f"data/council/{name}.jsonl")]
    save(org, [record(org, "uk_council_card", "card", "GBP", r) for r in rows if (r.get("amount") or 0) > 0])
json.dump(split, open("results/split.json", "w"), indent=1)
for part, orgs in split.items():
    print(part, len(orgs), sum(o["rows"] for o in orgs.values()))
print("STD DONE")
