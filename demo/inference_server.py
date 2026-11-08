"""Inference only: the fine-tuned decision model behind one endpoint. Runs on the GPU pod.
POST /predict {"state": str, "questions": {...}} -> {"answers": {qid: {"probabilities": {...}}}, "model": ..., "ms": ...}"""
import argparse, os, threading, time
import torch
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
import uvicorn
from unsloth import FastDecisionModel

ap = argparse.ArgumentParser(); ap.add_argument("--adapter", default="/workspace/v3/adapter"); ap.add_argument("--port", type=int, default=9000); ap.add_argument("--host", default="127.0.0.1"); A = ap.parse_args()
TOKEN = os.environ.get("MODEL_TOKEN", "")
model, tok = FastDecisionModel.from_pretrained(model_name=A.adapter, max_seq_length=8192, load_in_4bit=True); FastDecisionModel.for_inference(model)
VERSION = "qwen3-4b-v3-lora"; DEVICE = torch.cuda.get_device_name(0); LOCK = threading.Lock()
app = FastAPI(title="Coding model")


class Req(BaseModel):
    state: str; questions: dict


def check(token):
    if TOKEN and token != f"Bearer {TOKEN}":
        raise HTTPException(401, "Missing or wrong token.")


@app.get("/health")
def health(authorization: str = Header(default="")):
    check(authorization)
    return {"model": VERSION, "device": DEVICE}


@app.post("/predict")
def predict(r: Req, authorization: str = Header(default="")):
    check(authorization)
    t = time.time()
    with LOCK:  # one GPU, one request at a time
        a = FastDecisionModel.predict(model, tok, r.state, r.questions)
    return {"answers": {k: {"probabilities": v["probabilities"]} for k, v in a.items()}, "model": VERSION, "ms": round(1000 * (time.time() - t), 1)}


print("INFERENCE READY", VERSION, DEVICE, flush=True)
uvicorn.run(app, host=A.host, port=A.port, log_level="warning")
