"""Score a saved adapter. First re-scores 20 validation rows and checks they match the earlier run, then scores the test set once."""
import gzip, json, sys
from unsloth import FastDecisionModel
ADAPTER, OUTDIR, SETS = sys.argv[1], sys.argv[2], sys.argv[3:]
from common import questions
load = lambda p: [json.loads(l) for l in gzip.open(p, "rt")]
model, tok = FastDecisionModel.from_pretrained(model_name=ADAPTER, max_seq_length=8192, load_in_4bit=True); FastDecisionModel.for_inference(model)



Q = lambda r: questions(r["options"])


def score(r):
    a = FastDecisionModel.predict(model, tok, r["state"], Q(r)); p = a["account"]["probabilities"]; ranked = sorted(p, key=p.get, reverse=True); q = a["action"]["probabilities"]; best = max(q, key=q.get)
    return {"org": r["org"], "i": r.get("i"), "codes": ranked[:5], "conf": p[ranked[0]], "label": r["label"], "action": best, "action_prob": q[best], "action_probs": q}


ref = json.load(open("/workspace/data/v3_val_ref.json")); chk = [score(r) for r in load("/workspace/data/val_test.jsonl.gz")[:20]]
same = sum(a["codes"][0] == b["codes"][0] for a, b in zip(chk, ref)); gap = max(abs(a["conf"] - b["conf"]) for a, b in zip(chk, ref))
print("CHECK", json.dumps({"same_top1": same, "of": 20, "max_conf_gap": round(gap, 4)}), flush=True)
if same < 19 or gap > 0.05:
    print("CHECK FAILED: loaded model does not match the earlier v3 run; test set not scored", flush=True); sys.exit(1)
for name in SETS:
    out = []
    for n, r in enumerate(load(f"/workspace/data/{name}.jsonl.gz"), 1):
        out.append(score(r))
        if n % 200 == 0: print("PROGRESS", name, n, flush=True)
    json.dump(out, open(f"{OUTDIR}/{name}.json", "w")); print("SET DONE", name, len(out), flush=True)
print("TEST DONE", flush=True)
