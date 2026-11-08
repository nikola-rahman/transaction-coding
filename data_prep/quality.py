"""Data quality report for downloaded sources. Usage: quality.py RAW_DIR SOURCE..."""
import collections, glob, gzip, json, os, re, sys, datetime

FIELDS = {
    "ct": dict(merchant="vendor_name", account="expense_description", date="date", amount="amount", org="organization"),
    "fulton": dict(merchant="vendor_legal_name", account="object_name", date="disb_date", amount="amount", department="department_name"),
    "ramsey": dict(merchant="supplier_name", account="account_name", date="payment_date", amount="amount", department="department_name", memo="description"),
    "la": dict(merchant="vendor_name", account="account_name", date="transaction_date", amount="dollar_amount", department="department_name", memo="description"),
}
BAD = re.compile(r"^(n/?a|none|unknown|tbd|misc(ellaneous)?|various|null|\W*|redacted|withheld)$", re.I)
TODAY = datetime.date.today().isoformat()
raw = sys.argv[1]
report = {}
for src in sys.argv[2:]:
    f = FIELDS[src]; n = 0; blank = collections.Counter(); seen = set(); dup = 0
    amount_bad = neg = zero = future = date_bad = placeholder = 0
    accounts = collections.defaultdict(collections.Counter); merchant_accounts = collections.defaultdict(collections.Counter); years = collections.Counter(); lengths = 0
    for path in sorted(glob.glob(os.path.join(raw, src, "*.json.gz"))):
        for r in json.loads(gzip.decompress(open(path, "rb").read())):
            n += 1
            for k, c in f.items():
                if not str(r.get(c, "") or "").strip():
                    blank[k] += 1
            m = str(r.get(f["merchant"], "")).strip(); a = " ".join(str(r.get(f["account"], "")).split()).lower(); org = r.get(f.get("org", ""), src) if "org" in f else src
            placeholder += bool(BAD.match(m)); lengths += len(m)
            key = hash(tuple(str(r.get(c)) for c in f.values()))
            dup += key in seen; seen.add(key)
            try:
                v = float(r.get(f["amount"])); neg += v < 0; zero += v == 0
            except (TypeError, ValueError):
                amount_bad += 1
            d = str(r.get(f["date"], ""))[:10]
            if re.match(r"\d{4}-\d\d-\d\d", d):
                years[d[:4]] += 1; future += d > TODAY
            else:
                date_bad += 1
            accounts[org][a] += 1; merchant_accounts[(org, m.lower())][a] += 1
    repeat = [c for c in merchant_accounts.values() if sum(c.values()) >= 5]
    multi = sum(len(c) > 1 for c in repeat) / max(1, len(repeat))
    majority = sum(max(c.values()) for c in merchant_accounts.values()) / max(1, n)
    report[src] = {
        "rows": n, "orgs": len(accounts), "accounts_per_org": sorted(len(c) for c in accounts.values()), "top_account_share": round(max(max(c.values()) / sum(c.values()) for c in accounts.values()), 3),
        "blank_share": {k: round(blank[k] / n, 3) for k in f}, "exact_duplicate_share": round(dup / n, 3), "placeholder_merchant_share": round(placeholder / n, 4),
        "negative_amount_share": round(neg / n, 3), "zero_amount_share": round(zero / n, 3), "bad_amount": amount_bad, "future_dates": future, "bad_dates": date_bad,
        "merchants": len(merchant_accounts), "repeat_merchants_with_several_accounts": round(multi, 3), "best_case_merchant_lookup": round(majority, 3), "mean_merchant_length": round(lengths / n, 1),
        "rows_by_year": dict(sorted(years.items())),
    }
print(json.dumps(report, indent=1))
