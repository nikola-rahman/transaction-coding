"""Validation and test rows with rolling history: each row sees all of its organization's transactions before it.
Same rows, options and prompt as the frozen-history sets; only the history changes."""
import gzip, json, re, sys, collections
from common import load, prompt, retrieve, slug
for src_path, out_path in (("gen/eval/dev.jsonl.gz", "gen/eval/dev_rolling.jsonl.gz"), ("gen/eval/test.jsonl.gz", "gen/eval/test_rolling.jsonl.gz")):
    rows = [json.loads(l) for l in gzip.open(src_path, "rt")]; out = []; changed = 0
    for org in dict.fromkeys(r["org"] for r in rows):
        d = sorted((json.loads(l) for l in gzip.open(f"data/std/{slug(org)}.jsonl.gz", "rt")), key=lambda r: r["date"])
        for r in [x for x in rows if x["org"] == org]:
            t = d[r["i"]]; assert t["account"] == r["label"]
            sh = retrieve(d[:r["i"]], t); s = prompt(t, sh); changed += s != r["state"]
            opts = list(dict.fromkeys(r["options"] + [p["account"] for p in sh]))[:255]
            out.append({**r, "state": s, "options": opts})
    import os; os.makedirs("gen/eval", exist_ok=True)
    with gzip.open(out_path, "wt") as f:
        for x in out: f.write(json.dumps(x) + "\n")
    print(out_path, len(out), "rows whose shown history changed:", changed, "| options grew on", sum(len(a["options"]) != len(b["options"]) for a, b in zip(out, rows)))
