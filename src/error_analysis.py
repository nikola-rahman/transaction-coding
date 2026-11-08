"""Error analysis for the v3 recipe on validation sets, across two seeds. Sealed organizations are not used."""
import collections, gzip, json, re
rd = lambda p: [json.loads(l) for l in gzip.open(p, "rt")]
R = lambda run, n: json.load(open(f"results/development/fixed_history/{run}/{n}.json"))


def parse(state):
    m = re.search(r"merchant=(.*?); amount=([^ ]+)", state); head, _, past = state.partition("Similar past transactions at this organization:\n")
    same = []
    for l in past.split("\n"):
        if " -> " in l and l.split(" | ")[0].strip().lower() == m.group(1).strip().lower():
            same.append(l.rsplit(" -> ", 1)[1])
    n = len(same); k = len(set(same))
    return m.group(1), float(m.group(2)), ("new_merchant" if n == 0 else "several_accounts" if k > 1 else "thin" if n < 3 else "easy"), same


rows = rd("gen/eval/dev.jsonl.gz"); A, B = R("seed1", "dev"), R("seed2", "dev"); assert len(rows) == len(A) == len(B) and all(a["label"] == r["label"] == b["label"] for a, b, r in zip(A, B, rows))
T = []
for r, a, b in zip(rows, A, B):
    m, amt, case, same = parse(r["state"]); inopt = r["label"] in r["options"]; shown = r["label"] in r["state"].split("Similar past")[1]
    T.append(dict(org=r["org"], merchant=m, amount=amt, case=case, same=same, label=r["label"], in_shown=shown, a=a, b=b, state=r["state"]))
print("== account accuracy by case: rows, top1 s1/s2, top5 s1/s2, accept@.8 s1/s2 and wrong")
for grp in ("case", "org"):
    for k in sorted({t[grp] for t in T}):
        S = [t for t in T if t[grp] == k]; f = lambda s, fn: sum(fn(t[s]) and True for t in S)
        h1 = [round(100 * sum(t[s]["codes"][0] == t["label"] for t in S) / len(S), 1) for s in "ab"]; h5 = [round(100 * sum(t["label"] in t[s]["codes"] for t in S) / len(S), 1) for s in "ab"]
        acc = [[t for t in S if t[s]["action"] == "accept" and t[s]["conf"] >= .8] for s in "ab"]; w = [sum(t[s]["codes"][0] != t["label"] for t in x) for s, x in zip("ab", acc)]
        print(f"{k[:32]:32} {len(S):4} top1 {h1} top5 {h5} accepted {[len(x) for x in acc]} wrong {w}")
print("== miss types on top1 errors (both seeds wrong)")
both = [t for t in T if t["a"]["codes"][0] != t["label"] and t["b"]["codes"][0] != t["label"]]; one = sum((t["a"]["codes"][0] != t["label"]) != (t["b"]["codes"][0] != t["label"]) for t in T)
print("both wrong", len(both), "exactly one wrong", one, "both right", 1000 - len(both) - one, "same wrong answer", sum(t["a"]["codes"][0] == t["b"]["codes"][0] for t in both))
print("true account absent from shown history", sum(not t["in_shown"] for t in both), "of", len(both), "| overall absent", sum(not t["in_shown"] for t in T), "top1 when absent", round(100 * sum(t["a"]["codes"][0] == t["label"] for t in T if not t["in_shown"]) / max(1, sum(not t["in_shown"] for t in T)), 1), "when shown", round(100 * sum(t["a"]["codes"][0] == t["label"] for t in T if t["in_shown"]) / sum(t["in_shown"] for t in T), 1))
print("label outside top5 both seeds", sum(t["label"] not in t["a"]["codes"] and t["label"] not in t["b"]["codes"] for t in both))
print("== calibration, seed-pooled: conf bin, n, accuracy")
for lo, hi in ((0, .3), (.3, .5), (.5, .7), (.7, .8), (.8, .9), (.9, .95), (.95, 1.01)):
    x = [(t, s) for t in T for s in "ab" if lo <= t[s]["conf"] < hi]; print(lo, hi, len(x), round(100 * sum(t[s]["codes"][0] == t["label"] for t, s in x) / max(1, len(x)), 1))
print("== accept@.8 agreement across seeds")
ca = lambda t, s: t[s]["action"] == "accept" and t[s]["conf"] >= .8
print("both accept", sum(ca(t, "a") and ca(t, "b") for t in T), "one only", sum(ca(t, "a") != ca(t, "b") for t in T), "both accept+both wrong", sum(ca(t, "a") and ca(t, "b") and t["a"]["codes"][0] != t["label"] and t["b"]["codes"][0] != t["label"] for t in T), "both accept + same code", sum(ca(t, "a") and ca(t, "b") and t["a"]["codes"][0] == t["b"]["codes"][0] for t in T))
wrong = [t for t in T if (ca(t, "a") and t["a"]["codes"][0] != t["label"]) or (ca(t, "b") and t["b"]["codes"][0] != t["label"])]
json.dump([{k: v for k, v in t.items() if k not in ("a", "b")} | {"s1": t["a"]["codes"][:2], "c1": round(t["a"]["conf"], 2), "s2": t["b"]["codes"][:2], "c2": round(t["b"]["conf"], 2)} for t in wrong], open("results/development/wrong_accepts.json", "w"), indent=0)
print("wrong accept rows, either seed", len(wrong))
print("== actions")
sets = {"real_actions_held": "ra_held", "real_hard_held": "ra_hard_held", "real_person_held": None}; v3rows = rd("gen/training/ra_person_held.jsonl.gz"); AC = ["accept", "request_document", "ask_person", "lookup_merchant", "send_to_bookkeeper"]; dis = []
for name, f in sets.items():
    src = rd(f"gen/training/{f}.jsonl.gz") if f else v3rows; a, b = R("seed1", name), R("seed2", name); assert len(a) == len(b) == len(src)
    conf = collections.Counter(); stable = 0; cases = collections.defaultdict(lambda: [0, 0])
    for r, x, y in zip(src, a, b):
        conf[(r["action"], x["action"])] += 1; conf[(r["action"], y["action"])] += 1; both_wrong = x["action"] != r["action"] and y["action"] != r["action"]; stable += both_wrong
        c = parse(r["state"])[2]; cases[c][0] += 2; cases[c][1] += (x["action"] == r["action"]) + (y["action"] == r["action"])
        if both_wrong and x["action"] == y["action"]:
            dis.append({"set": name, "org": r["org"], "gold": r["action"], "pred": x["action"], "p": round(x["action_prob"], 2), "state": r["state"][:1500], "case": c})
    print(name, "rows", len(src), "wrong on both seeds", stable, {k: round(100 * v[1] / v[0], 1) for k, v in cases.items()})
    print("  gold\\pred", [x[:6] for x in AC])
    for g in AC:
        print(" ", g[:10].ljust(10), [conf[(g, p)] for p in AC])
    pr = {p: round(100 * conf[(p, p)] / max(1, sum(conf[(g, p)] for g in AC)), 1) for p in AC}; print("  precision", pr)
    # action confidence
    allr = [(r["action"] == x["action"], x["action_prob"]) for r, x in zip(src, a)] + [(r["action"] == y["action"], y["action_prob"]) for r, y in zip(src, b)]
    for lo, hi in ((0, .5), (.5, .7), (.7, .9), (.9, 1.01)):
        z = [c for c, p in allr if lo <= p < hi]; print("  prob", lo, hi, len(z), round(100 * sum(z) / max(1, len(z)), 1))
json.dump(dis, open("results/development/action_errors.json", "w"), indent=0); print("stable action errors", len(dis), collections.Counter((d["gold"], d["pred"]) for d in dis).most_common(10))
