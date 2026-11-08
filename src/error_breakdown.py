"""Why the model was wrong, on the rolling-history validation and test sets.
Each wrong row is put in one group using only the history the model was shown (never the label to decide what history settles)."""
import collections, contextlib, gzip, io, json, sys
sys.argv = ["x"]; sys.path.insert(0, "src")
with contextlib.redirect_stdout(io.StringIO()):
    import evidence as F

GROUPS = ["inconsistent coding: history pointed to another account", "inconsistent coding: mixed history, right answer a minority",
          "insufficient information: new merchant, no history", "near-duplicate account names", "model missed: history pointed to the right answer"]


def group(r, x, e):
    kind, says, n = e; pred = x["codes"][0]
    if F.twin(pred, r["label"]): return GROUPS[3]
    if says == r["label"]: return GROUPS[4]
    if kind == "new_merchant": return GROUPS[2]
    if kind == "mixed_history": return GROUPS[1]
    return GROUPS[0]


out = {}
for name, rows_p, pred_p in (("development", "gen/eval/dev_rolling.jsonl.gz", "results/development/rolling.json"), ("test", "gen/eval/test_rolling.jsonl.gz", "results/test/rolling.json")):
    rows = [json.loads(l) for l in gzip.open(rows_p, "rt")]; P = json.load(open(pred_p))
    wrong = [(r, x) for r, x in zip(rows, P) if x["codes"][0] != r["label"]]
    allc = collections.Counter(group(r, x, F.evidence(r)) for r, x in wrong)
    acc = [(r, x) for r, x in wrong if x["action"] == "accept"]; accc = collections.Counter(group(r, x, F.evidence(r)) for r, x in acc)
    routed = len(wrong) - len(acc); in5 = sum(r["label"] in x["codes"] for r, x in wrong)
    print(f"\n== {name}: {len(wrong)} wrong of {len(rows)}; right account in top 5 for {in5}; {routed} of the wrong rows were sent to a next step, {len(acc)} were 'approve'")
    for g in GROUPS: print(f"  {allc[g]:4} all wrong | {accc[g]:4} wrong and 'approve' | {g}")
    out[name] = {"rows": len(rows), "wrong": len(wrong), "wrong_in_top5": in5, "wrong_routed": routed, "wrong_approve": len(acc), "groups": {g: [allc[g], accc[g]] for g in GROUPS}}
json.dump(out, open("results/error_breakdown.json", "w"), indent=1)
