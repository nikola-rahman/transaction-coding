CREATE TABLE orgs (id TEXT PRIMARY KEY, name TEXT NOT NULL, currency TEXT NOT NULL);
CREATE TABLE accounts (id INTEGER PRIMARY KEY, org TEXT NOT NULL REFERENCES orgs(id), name TEXT NOT NULL, UNIQUE (org, name));
CREATE TABLE transactions (
  id INTEGER PRIMARY KEY, org TEXT NOT NULL REFERENCES orgs(id),
  merchant_name TEXT NOT NULL, amount REAL NOT NULL, currency TEXT NOT NULL, date TEXT NOT NULL,
  department TEXT, merchant_category TEXT, memo TEXT, payment_kind TEXT,
  account TEXT,                -- NULL until coded
  source TEXT,                 -- import | person | suggestion | bulk | rule
  coded_at TEXT, next_step TEXT, suggestion_id INTEGER,
  recorded_account TEXT,       -- demo only: what the organization actually recorded
  created_at TEXT DEFAULT (datetime('now')));
CREATE INDEX tx_org_merchant ON transactions (org, lower(merchant_name), date);
CREATE INDEX tx_org_uncoded ON transactions (org, account);
CREATE TABLE rules (id INTEGER PRIMARY KEY, org TEXT NOT NULL, pattern TEXT NOT NULL, match TEXT NOT NULL CHECK (match IN ('equals','contains')), account TEXT NOT NULL, created_at TEXT DEFAULT (datetime('now')));
CREATE TABLE suggestions (
  id INTEGER PRIMARY KEY, txn_id INTEGER NOT NULL, org TEXT NOT NULL, model_version TEXT NOT NULL,
  account TEXT NOT NULL, confidence REAL NOT NULL, top5 TEXT NOT NULL, action TEXT, action_probs TEXT,
  retrieved TEXT NOT NULL, rule_id INTEGER, latency_ms REAL, outcome TEXT,  -- outcome: accepted | changed | NULL
  created_at TEXT DEFAULT (datetime('now')));
CREATE INDEX sug_txn ON suggestions (txn_id, id);
CREATE TABLE events (id INTEGER PRIMARY KEY, org TEXT, txn_id INTEGER, kind TEXT NOT NULL, detail TEXT, at TEXT DEFAULT (datetime('now')));
