"""Coding Desk demo app, run locally: database, rules, as-of history retrieval in SQL, review workflow and UI.
The model runs elsewhere (the GPU pod) behind inference_server.py; this app calls it over HTTP, normally through an SSH tunnel.

  uv run --with fastapi --with uvicorn --with httpx demo/app.py            # model at http://127.0.0.1:9000
  MOCK=1 uv run --with fastapi --with uvicorn --with httpx demo/app.py     # no model: suggestions from history counts (UI work only)
"""
import argparse, collections, json, os, sqlite3, threading, time
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser(); ap.add_argument("--db", default=os.path.join(HERE, "demo.db")); ap.add_argument("--model-url", default=os.environ.get("MODEL_URL", "http://127.0.0.1:9000"))
ap.add_argument("--port", type=int, default=8000); ARGS = ap.parse_args()
MOCK = os.environ.get("MOCK") == "1"
SAFE = 0.9  # "safe to approve quickly": next step is accept and confidence at least this

# Same next-step definitions and question wording the model was trained with (src/train.py, src/common.py).
ACTIONS = {'accept': 'The evidence settles one account',
           'request_document': 'A receipt or invoice showing the item would settle it',
           'ask_person': 'Only the person who spent it knows the purpose or beneficiary',
           'lookup_merchant': "The merchant's business is unknown", 'send_to_bookkeeper': 'It needs accounting judgment, or the risk is high'}


def questions(options):
    return {"account": {"type": "choice", "instructions": "Which account should the new transaction be coded to?", "criteria": {o: o for o in options}},
            "action": {"type": "choice", "instructions": "What is the cheapest next step likely to settle the account?", "criteria": ACTIONS}}


def connect():
    c = sqlite3.connect(ARGS.db, check_same_thread=False, timeout=30); c.row_factory = sqlite3.Row; c.execute("PRAGMA journal_mode=WAL"); return c


DB = connect(); LOCK = threading.RLock(); WAKE = threading.Event()


def q(sql, *a):
    with LOCK:
        return [dict(r) for r in DB.execute(sql, a).fetchall()]


def x(sql, *a):
    with LOCK:
        cur = DB.execute(sql, a); DB.commit(); return cur.lastrowid


def event(org, txn_id, kind, **detail):
    x("INSERT INTO events (org, txn_id, kind, detail) VALUES (?,?,?,?)", org, txn_id, kind, json.dumps(detail))


# ---------- model ----------
class Model:
    """Client for the inference server. Falls back to nothing: if the model is unreachable, suggestions wait and retry."""
    def __init__(self):
        import httpx
        tok = os.environ.get("MODEL_TOKEN", ""); self.http = httpx.Client(base_url=ARGS.model_url, timeout=60, headers={"authorization": f"Bearer {tok}"} if tok else {})
        self.version, self.device = ("mock-history-counts", "laptop CPU (mock)") if MOCK else ("not connected", "unknown")

    def health(self):
        if MOCK:
            return True
        try:
            h = self.http.get("/health").json(); self.version, self.device = h["model"], h["device"]; return True
        except Exception:
            self.version, self.device = "not connected", "unknown"; return False

    def predict(self, state, options, shown):
        if MOCK:
            c = collections.Counter(p["account"] for p in shown)
            p = {o: (c.get(o, 0) + 0.2) for o in options}; s = sum(p.values()); p = {k: v / s for k, v in p.items()}
            top = max(p.values()); act = {"accept": top, "request_document": (1 - top) * .5, "ask_person": (1 - top) * .2, "lookup_merchant": (1 - top) * .2 if c else .6, "send_to_bookkeeper": (1 - top) * .1}
            s = sum(act.values()); return p, {k: v / s for k, v in act.items()}
        r = self.http.post("/predict", json={"state": state, "questions": questions(options)}); r.raise_for_status(); a = r.json()["answers"]
        return a["account"]["probabilities"], a["action"]["probabilities"]


# ---------- retrieval (as-of, SQL) and prompt: identical ranking and text to training (src/common.py) ----------
def retrieve(t, k=20):
    cands = q("""SELECT id, merchant_name, amount, currency, date, department, merchant_category, memo, account FROM transactions
                 WHERE org = ? AND account IS NOT NULL AND id != ? AND date <= ?
                   AND (lower(merchant_name) = lower(?) OR (? IS NOT NULL AND merchant_category = ?) OR (? IS NOT NULL AND department = ?))
                 ORDER BY date DESC, id DESC""", t["org"], t["id"], t["date"], t["merchant_name"], t["merchant_category"], t["merchant_category"], t["department"], t["department"])
    m = t["merchant_name"].lower(); d = t["department"]; c = t["merchant_category"]

    def rank(p):
        mm = p["merchant_name"].lower() == m; dd = bool(d) and p["department"] == d; cc = bool(c) and p["merchant_category"] == c
        return (mm and dd, mm, cc and dd, cc, dd)
    cands.sort(key=lambda p: (rank(p), p["date"]), reverse=True); picked, per = [], collections.Counter()
    for p in cands:
        if per[p["account"]] < 8:
            picked.append(p); per[p["account"]] += 1
        if len(picked) == k:
            break
    return picked


def prompt(t, shown):
    lines = "\n".join(f"{p['merchant_name']} | {p['amount']} | {p['department']} | {p['merchant_category']} | {p['memo']} -> {p['account']}" for p in shown) or "None available."
    return (f"New transaction: merchant={t['merchant_name']}; amount={t['amount']} {t['currency']}; date={t['date']}; department={t['department']}; "
            f"merchant category={t['merchant_category']}; memo={t['memo']}.\n\nSimilar past transactions at this organization:\n{lines}")


def matching_rule(t):
    for r in q("SELECT * FROM rules WHERE org = ? ORDER BY id", t["org"]):
        name, pat = t["merchant_name"].lower(), r["pattern"].lower()
        if (r["match"] == "equals" and name == pat) or (r["match"] == "contains" and pat in name):
            return r
    return None


def suggest(txn_id):
    t = q("SELECT * FROM transactions WHERE id = ?", txn_id)
    if not t or t[0]["account"] is not None:
        return
    t = t[0]; start = time.time(); rule = matching_rule(t)
    if rule:
        top5, conf, action, aprobs, shown, version = [rule["account"]], 1.0, "accept", {"accept": 1.0}, [], f"rule #{rule['id']}"
    else:
        shown = retrieve(t); chart = [a["name"] for a in q("SELECT name FROM accounts WHERE org = ? ORDER BY id", t["org"])]
        options = list(dict.fromkeys([p["account"] for p in shown] + chart))[:255]
        if len(options) < 2:
            return
        p, aprobs = MODEL.predict(prompt(t, shown), options, shown)
        top5 = sorted(p, key=p.get, reverse=True)[:5]; conf = p[top5[0]]; action = max(aprobs, key=aprobs.get); version = MODEL.version
        top5 = [[a, round(p[a], 4)] for a in top5]
    if rule:
        top5 = [[rule["account"], 1.0]]
    sid = x("""INSERT INTO suggestions (txn_id, org, model_version, account, confidence, top5, action, action_probs, retrieved, rule_id, latency_ms)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""", txn_id, t["org"], version, top5[0][0], conf, json.dumps(top5), action, json.dumps(aprobs),
            json.dumps([p["id"] for p in shown]), rule["id"] if rule else None, round(1000 * (time.time() - start), 1))
    x("UPDATE transactions SET suggestion_id = ? WHERE id = ? AND account IS NULL", sid, txn_id)


def worker():
    while True:
        if not MODEL.health():
            time.sleep(3); continue
        todo = q("SELECT id FROM transactions WHERE account IS NULL AND suggestion_id IS NULL ORDER BY date, id LIMIT 1")
        if not todo:
            WAKE.wait(5); WAKE.clear(); continue
        try:
            suggest(todo[0]["id"])
        except Exception as e:  # keep serving; record the failure on the transaction's timeline
            print("SUGGEST FAILED", todo[0]["id"], repr(e), flush=True); event(None, todo[0]["id"], "suggest_failed", error=repr(e)); time.sleep(2)


def refresh_similar(t):
    """History changed: suggestions for uncoded transactions of the same merchant or department are recomputed."""
    x("""UPDATE transactions SET suggestion_id = NULL WHERE org = ? AND account IS NULL
         AND (lower(merchant_name) = lower(?) OR (? IS NOT NULL AND department = ?))""", t["org"], t["merchant_name"], t["department"], t["department"])
    WAKE.set()


# ---------- API ----------
app = FastAPI(title="Coding Desk")


def txn_view(t):
    s = q("SELECT * FROM suggestions WHERE id = ?", t["suggestion_id"])[0] if t.get("suggestion_id") else None
    if s:
        s["top5"] = json.loads(s["top5"]); s["action_probs"] = json.loads(s["action_probs"] or "{}"); s["retrieved"] = json.loads(s["retrieved"])
        s["safe"] = s["action"] == "accept" and s["confidence"] >= SAFE
    return {**t, "suggestion": s}


def get_txn(tid):
    t = q("SELECT * FROM transactions WHERE id = ?", tid)
    if not t:
        raise HTTPException(404, "Transaction not found. It may have been deleted.")
    return t[0]


@app.get("/api/status")
def status():
    return {"model": MODEL.version, "device": MODEL.device, "mock": MOCK, "connected": MODEL.health(), "model_url": ARGS.model_url, "pending": q("SELECT count(*) n FROM transactions WHERE account IS NULL AND suggestion_id IS NULL")[0]["n"], "safe_threshold": SAFE}


@app.get("/api/orgs")
def orgs():
    return q("""SELECT o.*, (SELECT count(*) FROM transactions t WHERE t.org = o.id AND t.account IS NULL) inbox,
                (SELECT count(*) FROM transactions t WHERE t.org = o.id AND t.account IS NOT NULL) coded FROM orgs o ORDER BY name""")


@app.get("/api/inbox")
def inbox(org: str):
    return [txn_view(t) for t in q("SELECT * FROM transactions WHERE org = ? AND account IS NULL ORDER BY date DESC, id DESC", org)]


@app.get("/api/coded")
def coded(org: str, search: str = "", limit: int = 200):
    s = f"%{search.lower()}%"
    return q("""SELECT * FROM transactions WHERE org = ? AND account IS NOT NULL AND (lower(merchant_name) LIKE ? OR lower(account) LIKE ?)
                ORDER BY coded_at DESC, date DESC, id DESC LIMIT ?""", org, s, s, limit)


@app.get("/api/transactions/{tid}")
def detail(tid: int):
    t = txn_view(get_txn(tid)); s = t["suggestion"]
    if s and s["retrieved"]:
        ids = s["retrieved"]; rows = {r["id"]: r for r in q(f"SELECT * FROM transactions WHERE id IN ({','.join('?' * len(ids))})", *ids)}
        t["evidence"] = [rows[i] for i in ids if i in rows]
    else:
        t["evidence"] = []
    t["timeline"] = q("SELECT kind, detail, at FROM events WHERE txn_id = ? ORDER BY id", tid)
    return t


class NewTxn(BaseModel):
    org: str; merchant_name: str; amount: float; date: str
    department: str | None = None; merchant_category: str | None = None; memo: str | None = None


@app.post("/api/transactions")
def add(t: NewTxn):
    o = q("SELECT * FROM orgs WHERE id = ?", t.org)
    if not o:
        raise HTTPException(400, "Unknown company.")
    if not t.merchant_name.strip():
        raise HTTPException(400, "Enter a merchant name.")
    clean = lambda v: (v.strip() or None) if isinstance(v, str) else v
    tid = x("""INSERT INTO transactions (org, merchant_name, amount, currency, date, department, merchant_category, memo, payment_kind)
               VALUES (?,?,?,?,?,?,?,?, 'card')""", t.org, t.merchant_name.strip(), t.amount, o[0]["currency"], t.date, clean(t.department), clean(t.merchant_category), clean(t.memo))
    event(t.org, tid, "created"); WAKE.set(); return {"id": tid}


@app.delete("/api/transactions/{tid}")
def delete(tid: int):
    t = get_txn(tid); x("DELETE FROM transactions WHERE id = ?", tid); event(t["org"], tid, "deleted", merchant=t["merchant_name"])
    if t["account"]:
        refresh_similar(t)
    return {"ok": True}


class Code(BaseModel):
    account: str


def code_one(t, account, how):
    if not q("SELECT 1 FROM accounts WHERE org = ? AND name = ?", t["org"], account):
        raise HTTPException(400, f"'{account}' is not in this company's chart of accounts.")
    s = q("SELECT * FROM suggestions WHERE id = ?", t["suggestion_id"])[0] if t["suggestion_id"] else None
    source = how if (s and s["account"] == account) else "person"
    if s:
        x("UPDATE suggestions SET outcome = ? WHERE id = ?", "accepted" if s["account"] == account else "changed", s["id"])
    x("UPDATE transactions SET account = ?, source = ?, coded_at = datetime('now'), next_step = NULL WHERE id = ?", account, source, t["id"])
    event(t["org"], t["id"], "coded", account=account, source=source, suggested=s["account"] if s else None)
    refresh_similar(t)


@app.post("/api/transactions/{tid}/code")
def code(tid: int, c: Code):
    t = get_txn(tid)
    if t["account"]:
        raise HTTPException(409, "This transaction is already coded. Send it back to the inbox first.")
    code_one(t, c.account, "suggestion"); return {"ok": True}


@app.post("/api/transactions/{tid}/uncode")
def uncode(tid: int):
    t = get_txn(tid)
    x("UPDATE transactions SET account = NULL, source = NULL, coded_at = NULL, suggestion_id = NULL WHERE id = ?", tid)
    event(t["org"], tid, "sent_back", previous=t["account"]); refresh_similar(t); return {"ok": True}


class Step(BaseModel):
    step: str | None


@app.post("/api/transactions/{tid}/next_step")
def next_step(tid: int, s: Step):
    t = get_txn(tid)
    if s.step and s.step not in ACTIONS:
        raise HTTPException(400, "Unknown next step.")
    x("UPDATE transactions SET next_step = ? WHERE id = ?", s.step, tid); event(t["org"], tid, "next_step", step=s.step); return {"ok": True}


@app.post("/api/bulk_approve")
def bulk(org: str):
    n = 0
    for t in inbox(org):
        if t["suggestion"] and t["suggestion"]["safe"]:
            code_one(get_txn(t["id"]), t["suggestion"]["account"], "bulk"); n += 1
    return {"approved": n}


@app.get("/api/accounts")
def accounts(org: str):
    return q("""SELECT a.id, a.name, (SELECT count(*) FROM transactions t WHERE t.org = a.org AND t.account = a.name) used
                FROM accounts a WHERE a.org = ? ORDER BY a.id""", org)


class Acct(BaseModel):
    org: str; name: str


@app.post("/api/accounts")
def add_account(a: Acct):
    name = a.name.strip().lower()
    if not name:
        raise HTTPException(400, "Enter an account name.")
    if q("SELECT 1 FROM accounts WHERE org = ? AND name = ?", a.org, name):
        raise HTTPException(409, "That account already exists.")
    x("INSERT INTO accounts (org, name) VALUES (?,?)", a.org, name); event(a.org, None, "account_added", name=name)
    x("UPDATE transactions SET suggestion_id = NULL WHERE org = ? AND account IS NULL", a.org); WAKE.set(); return {"ok": True}


@app.delete("/api/accounts/{aid}")
def del_account(aid: int):
    a = q("SELECT * FROM accounts WHERE id = ?", aid)
    if not a:
        raise HTTPException(404, "Account not found.")
    a = a[0]; used = q("SELECT count(*) n FROM transactions WHERE org = ? AND account = ?", a["org"], a["name"])[0]["n"]
    if used:
        raise HTTPException(409, f"{used} transactions are coded to this account. Recode them before deleting it.")
    if q("SELECT 1 FROM rules WHERE org = ? AND account = ?", a["org"], a["name"]):
        raise HTTPException(409, "A rule uses this account. Delete the rule first.")
    x("DELETE FROM accounts WHERE id = ?", aid); event(a["org"], None, "account_deleted", name=a["name"])
    x("UPDATE transactions SET suggestion_id = NULL WHERE org = ? AND account IS NULL", a["org"]); WAKE.set(); return {"ok": True}


@app.get("/api/rules")
def rules(org: str):
    return q("SELECT * FROM rules WHERE org = ? ORDER BY id", org)


class Rule(BaseModel):
    org: str; pattern: str; match: str; account: str


@app.post("/api/rules")
def add_rule(r: Rule):
    if r.match not in ("equals", "contains") or not r.pattern.strip():
        raise HTTPException(400, "Enter merchant text and choose how it matches.")
    if not q("SELECT 1 FROM accounts WHERE org = ? AND name = ?", r.org, r.account):
        raise HTTPException(400, "Choose an account from the chart.")
    rid = x("INSERT INTO rules (org, pattern, match, account) VALUES (?,?,?,?)", r.org, r.pattern.strip(), r.match, r.account)
    event(r.org, None, "rule_added", id=rid, pattern=r.pattern, account=r.account)
    x("UPDATE transactions SET suggestion_id = NULL WHERE org = ? AND account IS NULL", r.org); WAKE.set(); return {"id": rid}


@app.delete("/api/rules/{rid}")
def del_rule(rid: int):
    r = q("SELECT * FROM rules WHERE id = ?", rid)
    if not r:
        raise HTTPException(404, "Rule not found.")
    x("DELETE FROM rules WHERE id = ?", rid); event(r[0]["org"], None, "rule_deleted", id=rid)
    x("UPDATE transactions SET suggestion_id = NULL WHERE org = ? AND account IS NULL", r[0]["org"]); WAKE.set(); return {"ok": True}


@app.get("/api/metrics")
def metrics(org: str):
    rev = q("SELECT s.*, t.account final FROM suggestions s JOIN transactions t ON t.id = s.txn_id WHERE s.org = ? AND s.outcome IS NOT NULL AND t.account IS NOT NULL", org)
    for r in rev:
        r["top5"] = [a for a, _ in json.loads(r["top5"])]
    bins = [(0, .5), (.5, .7), (.7, .9), (.9, 1.01)]
    cal = [{"bin": f"{int(lo*100)}–{min(100, int(hi*100))}%", "n": len(b), "right": round(100 * sum(r["final"] == r["account"] for r in b) / len(b), 1) if b else None}
           for lo, hi in bins for b in [[r for r in rev if lo <= r["confidence"] < hi]]]
    lat = [r["latency_ms"] for r in q("SELECT latency_ms FROM suggestions WHERE org = ? AND rule_id IS NULL ORDER BY id DESC LIMIT 200", org) if r["latency_ms"]]
    src = {r["source"]: r["n"] for r in q("SELECT source, count(*) n FROM transactions WHERE org = ? AND account IS NOT NULL AND source != 'import' GROUP BY source", org)}
    n = len(rev); right = sum(r["final"] == r["account"] for r in rev)
    return {"reviewed": n, "right": round(100 * right / n, 1) if n else None,
            "top5": round(100 * sum(r["final"] in r["top5"] for r in rev) / n, 1) if n else None,
            "changed": n - right, "calibration": cal, "sources": src,
            "latency_ms": {"median": sorted(lat)[len(lat) // 2] if lat else None, "count": len(lat)},
            "recent": q("SELECT e.kind, e.detail, e.at, t.merchant_name FROM events e LEFT JOIN transactions t ON t.id = e.txn_id WHERE e.org = ? ORDER BY e.id DESC LIMIT 25", org)}


@app.post("/api/demo/reset_inbox")
def reset(org: str):
    """Demo helper: send everything coded during the session back to the inbox."""
    ids = [r["id"] for r in q("SELECT id FROM transactions WHERE org = ? AND source IS NOT NULL AND source != 'import'", org)]
    x("UPDATE transactions SET account = NULL, source = NULL, coded_at = NULL, suggestion_id = NULL, next_step = NULL WHERE org = ? AND source IS NOT NULL AND source != 'import'", org)
    event(org, None, "inbox_reset", count=len(ids)); WAKE.set(); return {"reset": len(ids)}


app.mount("/static", StaticFiles(directory=os.path.join(HERE, "static")), name="static")


@app.get("/")
def index():
    return FileResponse(os.path.join(HERE, "static", "index.html"))


if __name__ == "__main__":
    MODEL = Model(); print("MODEL", "connected" if MODEL.health() else "not connected yet", MODEL.version, MODEL.device, flush=True)
    threading.Thread(target=worker, daemon=True).start()
    uvicorn.run(app, host="127.0.0.1", port=ARGS.port, log_level="warning")
