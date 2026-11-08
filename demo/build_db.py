"""Build the demo database from two validation organizations: real coded history plus an inbox of uncoded transactions.
The recorded account of each inbox row is kept in a demo-only column, so you can compare what the council actually coded."""
import gzip, json, re, sqlite3, sys, collections, os
ORGS = {"council:cambridgeshire": "Cambridgeshire County Council", "ct:Connecticut Airport Authority": "Connecticut Airport Authority"}
HISTORY, INBOX = 3000, 60
slug = lambda o: re.sub(r"[^a-zA-Z0-9]+", "_", o)[:60]
out = sys.argv[1] if len(sys.argv) > 1 else "demo/demo.db"
if os.path.exists(out): os.remove(out)
db = sqlite3.connect(out); db.executescript(open("demo/schema.sql").read())
for org, name in ORGS.items():
    rows = sorted((json.loads(l) for l in gzip.open(f"data/std/{slug(org)}.jsonl.gz", "rt")), key=lambda r: r["date"])
    hist, inbox = rows[:HISTORY], rows[HISTORY:HISTORY + INBOX]
    db.execute("INSERT INTO orgs VALUES (?,?,?)", (org, name, rows[0]["currency"]))
    counts = collections.Counter(r["account"] for r in rows[:HISTORY + INBOX])  # chart: accounts in use, most used first
    for a, _ in counts.most_common(): db.execute("INSERT INTO accounts (org, name) VALUES (?,?)", (org, a))
    f = lambda r: (org, r["merchant_name"], r["amount"], r["currency"], r["date"], r["department"], r["merchant_category"], r["memo"], r["payment_kind"])
    db.executemany("INSERT INTO transactions (org, merchant_name, amount, currency, date, department, merchant_category, memo, payment_kind, account, source, coded_at) VALUES (?,?,?,?,?,?,?,?,?,?, 'import', ?)", [f(r) + (r["account"], r["date"]) for r in hist])
    db.executemany("INSERT INTO transactions (org, merchant_name, amount, currency, date, department, merchant_category, memo, payment_kind, recorded_account) VALUES (?,?,?,?,?,?,?,?,?,?)", [f(r) + (r["account"],) for r in inbox])
    print(name, "history", len(hist), hist[0]["date"], "to", hist[-1]["date"], "| inbox", len(inbox), inbox[0]["date"], "to", inbox[-1]["date"], "| accounts", len(counts))
db.commit()
