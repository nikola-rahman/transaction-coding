"""Was the answer in the evidence the model saw? Rules use only the shown history, never the label, to decide what the evidence settles."""
import collections, gzip, json, re, sys
from difflib import SequenceMatcher
rows = [json.loads(l) for l in gzip.open("gen/eval/dev.jsonl.gz", "rt")]
M = {n: json.load(open(f"results/development/fixed_history/{n}/dev.json")) for n in ("seed1", "seed2")}
for n, v in M.items():
    assert [(x["org"], x["i"]) for x in v] == [(r["org"], r["i"]) for r in rows], n


def parse(state):
    head, hist = state.split("Similar past transactions at this organization:")
    m = re.search(r"merchant=(.*?); amount=([-\d.]+)", head); merchant, amount = m.group(1).strip().lower(), float(m.group(2))
    past = []
    for line in hist.strip().splitlines():
        if " -> " in line:
            left, acc = line.rsplit(" -> ", 1); f = [x.strip() for x in left.split(" | ")]
            try:
                past.append((f[0].lower(), float(f[1]), acc.strip()))
            except (ValueError, IndexError):
                pass
    return merchant, amount, past


def evidence(r):
    """What the shown history settles, without looking at the label."""
    merchant, amount, past = parse(r["state"]); same = [p for p in past if p[0] == merchant]
    exact = collections.Counter(p[2] for p in same if abs(p[1] - amount) <= max(0.01, 0.005 * abs(amount)))
    if exact and len(exact) == 1 and sum(exact.values()) >= 1:
        return "settled_by_same_amount", next(iter(exact)), len(same)
    c = collections.Counter(p[2] for p in same)
    if not same:
        return "new_merchant", None, 0
    top, k = c.most_common(1)[0]
    if len(same) >= 3 and k / len(same) >= 0.8:
        return "settled_by_history", top, len(same)
    if len(c) == 1:
        return "thin_one_account", top, len(same)
    return "mixed_history", top, len(same)


twin = lambda a, b: a != b and SequenceMatcher(None, a.lower(), b.lower()).ratio() >= 0.85
E = [evidence(r) for r in rows]
SETTLED = ("settled_by_same_amount", "settled_by_history")


def verdict_wrong_accept(r, x, e):
    kind, says, n = e; pred = x["codes"][0]
    if twin(pred, r["label"]):
        return "forgivable: near-duplicate account name"
    if kind in SETTLED and says == pred:
        return "forgivable: evidence pointed to the model's answer"
    if kind in SETTLED and says == r["label"]:
        return "not forgivable: evidence settled the right answer"
    if kind in SETTLED:
        return "not forgivable: evidence settled a third account"
    return f"not forgivable: should have asked ({kind})"


def verdict_routed(r, x, e):
    kind, says, n = e
    if kind in SETTLED and says == r["label"]:
        return "ask not needed: evidence settled the right answer"
    if kind in SETTLED:
        return "ask lucky: evidence looked settled but pointed wrong"
    return f"ask needed: {kind}"


out = {}
for name in ("seed1", "seed2"):
    A = M[name]; wa = collections.Counter(); ro = collections.Counter(); rr = collections.Counter(); acc = collections.Counter(); tot = collections.Counter(); per = []
    for r, x, e in zip(rows, A, E):
        ok = x["codes"][0] == r["label"]; tot[e[0]] += 1; acc[e[0]] += ok
        accepted = x["action"] == "accept"
        if accepted and not ok:
            v = verdict_wrong_accept(r, x, e); wa[v] += 1; per.append({"org": r["org"], "i": r["i"], "type": "wrong_accept", "verdict": v, "evidence": e[0], "evidence_says": e[1], "same_merchant_rows": e[2], "pred": x["codes"][0], "label": r["label"], "conf": x["conf"]})
        if not accepted:
            v = verdict_routed(r, x, e); (ro if ok else rr)[v] += 1
            per.append({"org": r["org"], "i": r["i"], "type": "routed_right" if ok else "routed_wrong", "verdict": v, "evidence": e[0], "evidence_says": e[1], "same_merchant_rows": e[2], "pred": x["codes"][0], "label": r["label"], "conf": x["conf"]})
    print(f"\n=== {name}: accepted {sum(x['action']=='accept' for x in A)}, wrong accepted {sum(wa.values())}")
    for k, v in wa.most_common(): print(f"  WRONG ACCEPT  {v:4}  {k}")
    for k, v in ro.most_common(): print(f"  ROUTED RIGHT  {v:4}  {k}")
    for k, v in rr.most_common(): print(f"  ROUTED WRONG  {v:4}  {k}")
    print("  top-1 by evidence:", {k: f"{tot[k]} rows {100*acc[k]/tot[k]:.1f}" for k in tot})
    out[name] = per
json.dump(out, open("results/development/evidence_verdicts.json", "w"), indent=0)
