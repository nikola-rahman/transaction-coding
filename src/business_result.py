"""Business result on rolling-history predictions.
1. Automation versus error: how many transactions can be marked safe at a target error rate, with the threshold chosen on development.
2. Per-company calibration: each company's threshold is set from its own earlier reviewed transactions, then applied to its later ones.
3. Review time per 1,000 transactions under stated assumptions, for no help, vendor rules, and the model."""
import collections, gzip, json, re
from common import slug
SETS = {"development": ("gen/eval/dev_rolling.jsonl.gz", "results/development/rolling.json"), "test": ("gen/eval/test_rolling.jsonl.gz", "results/test/rolling.json")}
TARGETS = [0.01, 0.02, 0.05, 0.10]


def load(name):
    rows = [json.loads(l) for l in gzip.open(SETS[name][0], "rt")]; P = json.load(open(SETS[name][1])); D = {}
    for o in {r["org"] for r in rows}:
        D[o] = sorted((json.loads(l) for l in gzip.open(f"data/std/{slug(o)}.jsonl.gz", "rt")), key=lambda r: r["date"])
    out = []
    for r, x in zip(rows, P):
        d = D[r["org"]]; t = d[r["i"]]; m = t["merchant_name"].lower()
        c = collections.Counter(p["account"] for p in d[:r["i"]] if p["merchant_name"].lower() == m)
        out.append({"org": r["org"], "date": t["date"], "i": r["i"], "conf": x["conf"], "approve": x["action"] == "accept", "right": x["codes"][0] == r["label"],
                    "top5": r["label"] in x["codes"], "rule": c.most_common(1)[0][0] if c else None, "label": r["label"]})
    return out


def threshold(rows, target, min_n=20):
    """Lowest confidence threshold whose 'approve' rows meet the target error, with at least min_n rows."""
    best = None
    for th in sorted({r["conf"] for r in rows}, reverse=True):
        a = [r for r in rows if r["approve"] and r["conf"] >= th]
        if len(a) >= min_n and sum(not r["right"] for r in a) / len(a) <= target:
            best = th
    return best


def apply(rows, th):
    a = [r for r in rows if th is not None and r["approve"] and r["conf"] >= th]; w = sum(not r["right"] for r in a)
    return len(a), w


dev, test = load("development"), load("test")
res = {"automation": [], "per_company": [], "time": {}}
print("== Automation versus error (threshold chosen on development, applied to test)")
print(f"{'target error':>12} | {'threshold':>9} | {'dev safe':>9} {'dev error':>9} | {'test safe':>9} {'test error':>10}")
for t in TARGETS:
    th = threshold(dev, t); dn, dw = apply(dev, th); tn, tw = apply(test, th)
    print(f"{t:>12.0%} | {th:>9.3f} | {dn/len(dev):>9.1%} {dw/max(1,dn):>9.1%} | {tn/len(test):>9.1%} {tw/max(1,tn):>10.1%}")
    res["automation"].append({"target": t, "threshold": th, "dev_safe": dn / len(dev), "dev_error": dw / max(1, dn), "test_safe": tn / len(test), "test_error": tw / max(1, tn)})

print("\n== Per-company calibration: threshold from each company's first half of transactions (by date), evaluated on its second half")
for name, rows in (("development", dev), ("test", test)):
    for t in (0.02, 0.05):
        g_th = threshold(dev, t); gn = gw = cn = cw = 0; nrows = 0
        for o in sorted({r["org"] for r in rows}):
            rs = sorted([r for r in rows if r["org"] == o], key=lambda r: (r["date"], r["i"])); half = len(rs) // 2; cal, ev = rs[:half], rs[half:]
            c_th = threshold(cal, t, min_n=10); a, b = apply(ev, g_th); gn += a; gw += b; a, b = apply(ev, c_th if c_th is not None else 1.01); cn += a; cw += b; nrows += len(ev)
        print(f"  {name:11} target {t:.0%}: one threshold for all -> {gn/nrows:5.1%} safe, {gw/max(1,gn):5.1%} wrong | per company -> {cn/nrows:5.1%} safe, {cw/max(1,cn):5.1%} wrong  ({nrows} evaluation rows)")
        res["per_company"].append({"set": name, "target": t, "global_safe": gn / nrows, "global_error": gw / max(1, gn), "company_safe": cn / nrows, "company_error": cw / max(1, cn), "rows": nrows})

# Review time per transaction, in seconds: (low, high). These are assumptions, not measurements.
A = {"manual": (30, 60), "approve_shown": (3, 6), "skim_safe": (1, 2), "fix_from_top5": (10, 20), "search_chart": (30, 60)}
print("\n== Review time per 1,000 transactions (hours), assumptions in seconds:", A)
for name, rows in (("development", dev), ("test", test)):
    th = 0.9  # the app's safe-to-approve rule: next step is approve and confidence >= 0.9
    for k in (0, 1):
        manual = A["manual"][k] * len(rows)
        rule = sum(A["approve_shown"][k] if r["rule"] == r["label"] else (A["search_chart"][k] if r["rule"] else A["manual"][k]) for r in rows)
        model = 0; silent = 0
        for r in rows:
            if r["approve"] and r["conf"] >= th:
                model += A["skim_safe"][k]; silent += not r["right"]
            elif r["right"]: model += A["approve_shown"][k]
            elif r["top5"]: model += A["fix_from_top5"][k]
            else: model += A["search_chart"][k]
        f = 1000 / len(rows) / 3600
        res["time"].setdefault(name, []).append({"assumption": ["low", "high"][k], "manual_h": manual * f, "rules_h": rule * f, "model_h": model * f, "silent_errors_per_1000": silent * 1000 / len(rows)})
        print(f"  {name:11} {['low','high'][k]:4} times: no help {manual*f:5.1f} h | vendor rules {rule*f:5.1f} h | model {model*f:5.1f} h  (wrong codes skimmed as safe: {silent*1000/len(rows):.0f} per 1,000)")
json.dump(res, open("results/business.json", "w"), indent=1)
