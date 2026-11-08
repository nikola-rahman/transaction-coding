"""Decision model for account and next action. Sources set by environment variables; test sets stay fixed."""
import collections, gzip, json, os, random, time
import torch
from unsloth import FastDecisionModel, DecisionTrainer, is_bfloat16_supported
from datasets import Dataset
from transformers import TrainerCallback, TrainingArguments

SEED = int(os.environ.get("SEED", 3407)); RUN = os.environ["RUN"]; MIX = os.environ["MIX"]; SMOKE = os.environ.get("SMOKE") == "1"
NAME, MAX_LEN, VAL_EVERY, ROOT = "unsloth/Qwen3-4B", 8192, 200, "/workspace/data2"
from common import ACTIONS, questions
load = lambda n: [json.loads(l) for l in gzip.open(f"{ROOT}/{n}.jsonl.gz", "rt")]
val = load("monitor"); test = load("dev"); act_held = load("ra_held"); hard_held = load("ra_hard_held"); person_held = load("ra_person_held"); gen_held = load("gen_held")
train = []
for part in MIX.split(","):  # name:repeats
    n, k = part.split(":"); train += load(n) * int(k)
random.Random(SEED).shuffle(train)
if SMOKE:
    train, val, test, act_held, hard_held, person_held, gen_held = train[:64], val[:8], test[:8], act_held[:8], hard_held[:8], person_held[:8], gen_held[:8]
print("RUN", RUN, "train", len(train), "with actions", sum("action" in r for r in train), flush=True)


def Q(r, with_action=True):
    return questions(r["options"], with_action)


model, tok = FastDecisionModel.from_pretrained(model_name=NAME, max_seq_length=MAX_LEN, load_in_4bit=True)
model = FastDecisionModel.get_peft_model(model, r=16, lora_alpha=16, lora_dropout=0, use_gradient_checkpointing="unsloth", random_state=SEED)
rows = []
for r in train:
    has = "action" in r; gold = {"account": r["label"]}
    if has:
        gold["action"] = r["action"]
    rows.append({"state": r["state"], "questions": json.dumps(Q(r, has)), "gold": json.dumps(gold)})
items, report = FastDecisionModel.build_dataset(Dataset.from_list(rows), tok, model)
print("build", {k: v for k, v in report.items() if not isinstance(v, (list, dict))}, flush=True)
train_items, eval_items = FastDecisionModel.split_holdout(items, seed=SEED)


def run(data, name, with_action, keep=False):
    FastDecisionModel.for_inference(model); out = []; start = time.time(); h1 = h5 = ah = 0; confusion = collections.Counter()
    for r in data:
        a = FastDecisionModel.predict(model, tok, r["state"], Q(r, with_action)); p = a["account"]["probabilities"]; ranked = sorted(p, key=p.get, reverse=True)
        h1 += ranked[0] == r["label"]; h5 += r["label"] in ranked[:5]; row = {"org": r["org"], "i": r.get("i"), "case": r.get("case"), "codes": ranked[:5], "conf": p[ranked[0]], "label": r["label"]}
        if with_action:
            q = a["action"]["probabilities"]; best = max(q, key=q.get); row.update(action=best, action_prob=q[best], action_probs=q)
            if "action" in r:
                ah += best == r["action"]; confusion[(r["action"], best)] += 1; row["gold_action"] = r["action"]; row["gold_b"] = r.get("action_b")
        out.append(row)
    res = {"set": name, "rows": len(data), "top1": round(100 * h1 / len(data), 1), "top5": round(100 * h5 / len(data), 1), "seconds": round(time.time() - start)}
    if confusion:
        res["action_accuracy"] = round(100 * ah / len(data), 1); res["recall"] = {k: round(100 * confusion[(k, k)] / max(1, sum(v for (g, _), v in confusion.items() if g == k)), 1) for k in ACTIONS}
    print("RESULT" if keep else "VAL", json.dumps(res), flush=True); return out, res


class Validate(TrainerCallback):
    def on_step_end(self, args, state, control, **kwargs):
        if state.global_step % VAL_EVERY == 0:
            print("STEP", state.global_step, "peak_gb", round(torch.cuda.max_memory_allocated() / 2**30, 1), flush=True); run(val, "validation", False); run(act_held[:100], "real_action_validation", True); FastDecisionModel.for_training(model); model.train()
        return control


trainer = DecisionTrainer(model=model, processing_class=tok, train_dataset=train_items, eval_dataset=eval_items, callbacks=[Validate()], args=TrainingArguments(
    per_device_train_batch_size=1, gradient_accumulation_steps=16, warmup_steps=15, num_train_epochs=1, max_steps=3 if SMOKE else -1, learning_rate=2e-4, lr_scheduler_type="cosine", weight_decay=0.01,
    bf16=is_bfloat16_supported(), fp16=not is_bfloat16_supported(), eval_strategy="no", logging_steps=10, output_dir=f"/workspace/out/{RUN}", report_to="none", seed=SEED, save_strategy="no"))
trainer.train()
print("PEAK_GB", round(torch.cuda.max_memory_allocated() / 2**30, 1), flush=True)
print("CALIBRATE", FastDecisionModel.calibrate(model, tok, eval_items), flush=True)
model.save_pretrained(f"/workspace/out/{RUN}/adapter")
results = {}
for name, data in (("dev", test), ("real_actions_held", act_held), ("real_hard_held", hard_held), ("real_person_held", person_held), ("generated_held", gen_held)):
    p, res = run(data, name, True, keep=True); results[name] = res; json.dump(p, open(f"/workspace/out/{RUN}/{name}.json", "w"))
json.dump(results, open(f"/workspace/out/{RUN}/summary.json", "w"), indent=1)
print("RUN DONE", RUN, flush=True)
