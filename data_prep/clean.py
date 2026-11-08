"""Build the cleaned training set from downloaded sources, and record what was removed and why."""
import collections, glob, gzip, json, os, re

RAW, OUT, TODAY = "data/raw", "data/clean", "2026-11-06"
os.makedirs(OUT, exist_ok=True)
SOURCES = {
    "ct": dict(merchant="vendor_name", account="expense_description", date="date", amount="amount", org="organization"),
    "fulton": dict(merchant="vendor_legal_name", account="object_name", date="disb_date", amount="amount", area="department_name"),
    "ramsey": dict(merchant="supplier_name", account="account_name", date="payment_date", amount="amount", area="department_name"),  # memo excluded: it repeats the account
    "la": dict(merchant="vendor_name", account="account_name", date="transaction_date", amount="dollar_amount", area="department_name", memo="description"),
}
orgs = collections.defaultdict(list); removed = collections.Counter(); seen = collections.defaultdict(set); raw_rows = collections.Counter()
for src, f in SOURCES.items():
    for path in sorted(glob.glob(f"{RAW}/{src}/*.json.gz")):
        for r in json.loads(gzip.decompress(open(path, "rb").read())):
            raw_rows[src] += 1
            merchant = str(r.get(f["merchant"], "") or "").strip(); account = " ".join(str(r.get(f["account"], "") or "").split()).lower(); date = str(r.get(f["date"], "") or "")[:10]
            try:
                amount = float(r.get(f["amount"]))
            except (TypeError, ValueError):
                removed[src, "bad_amount"] += 1; continue
            if not merchant or not account:
                removed[src, "blank_merchant_or_account"] += 1; continue
            if not re.match(r"\d{4}-\d\d-\d\d", date):
                removed[src, "bad_date"] += 1; continue
            if date > TODAY:
                removed[src, "future_date"] += 1; continue
            if amount <= 0:
                removed[src, "zero_or_negative_amount"] += 1; continue
            if "redacted" in merchant.lower():
                removed[src, "redacted_merchant"] += 1; continue
            if src == "la" and (not str(r.get("account_code", "")).startswith("0") or "fund" in account or account == "available"):
                removed[src, "la_non_expense_account"] += 1; continue
            org = f"{src}:{r.get(f['org'])}" if "org" in f else src
            area = str(r.get(f.get("area", ""), "") or "").strip().lower(); memo = str(r.get(f.get("memo", ""), "") or "").strip().lower()[:120]
            key = hash((merchant.lower(), account, date, amount, area, memo))
            if key in seen[org]:
                removed[src, "exact_duplicate"] += 1; continue
            seen[org].add(key)
            orgs[org].append({"org": org, "merchant": merchant, "label": account, "date": date, "amount": amount, "area": area, "memo": memo, "merchant_category": ""})
summary = {"raw_rows": dict(raw_rows), "removed": {f"{a}:{b}": n for (a, b), n in sorted(removed.items())}, "orgs": {}}
for org, rows in orgs.items():
    labels = collections.Counter(r["label"] for r in rows)
    if len(rows) < 200 or len(labels) < 5:
        summary["removed"][f"too_small:{org}"] = len(rows); continue
    with gzip.open(f"{OUT}/{re.sub(r'[^a-zA-Z0-9]+', '_', org)[:60]}.jsonl.gz", "wt") as f:
        for r in sorted(rows, key=lambda x: x["date"]):
            f.write(json.dumps(r) + "\n")
    summary["orgs"][org] = {"rows": len(rows), "accounts": len(labels), "merchants": len({r["merchant"].lower() for r in rows}), "from": min(r["date"] for r in rows), "to": max(r["date"] for r in rows), "memo_share": round(sum(bool(r["memo"]) for r in rows) / len(rows), 3)}
summary["total_rows"] = sum(o["rows"] for o in summary["orgs"].values())
json.dump(summary, open("results/clean_summary.json", "w"), indent=1)
print("CLEAN DONE", summary["total_rows"], len(summary["orgs"]))
