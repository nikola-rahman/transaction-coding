"""Join subagent labels to their real rows, in the decision model's state format."""
import glob, gzip, json
meta = {m["id"]: m for m in json.load(open("labels/real_meta.json"))}; L = {}
for f in sorted(glob.glob("labels/out/real_*_A.jsonl")):
    for l in open(f):
        d = json.loads(l); L[d["id"]] = d
out = {"train": [], "held": []}
for f in sorted(glob.glob("labels/batches/real_*.jsonl")):
    for l in open(f):
        x = json.loads(l); t = x["transaction"]; m = meta[x["id"]]; lab = L[x["id"]]
        lines = "\n".join(f"{p['merchant']} | {p['amount']} | {p['department']} | {p['merchant_category']} | {p['memo']} -> {p['account']}" for p in x["past_transactions"]) or "None available."
        s = f"New transaction: merchant={t['merchant']}; amount={t['amount']} {t['currency']}; date={t['date']}; department={t['department']}; merchant category={t['merchant_category']}; memo={t['memo']}; card=None; receipt=None.\n\nSimilar past transactions at this organization:\n{lines}"
        options = sorted(set(x["accounts_sample"]) | {m["recorded"]})
        out["held" if m["held_out"] else "train"].append({"org": m["org"], "state": s, "options": options, "label": m["recorded"], "action": lab["action"], "unknown": lab["unknown"]})
for k, v in out.items():
    with gzip.open(f"gen/real_actions_{k}.jsonl.gz", "wt") as f:
        for r in v:
            f.write(json.dumps(r) + "\n")
print({k: len(v) for k, v in out.items()})
