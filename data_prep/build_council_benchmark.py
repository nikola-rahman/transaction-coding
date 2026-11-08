"""Build the real-data scoreboard from cached council card files.

Usage: build_council_benchmark.py CENSUS_JSON CACHE_DIR OUT_DIR
Fetching is separate. This script only parses files already on disk as data.
"""
import collections, csv, datetime as dt, hashlib, io, json, math, os, random, re, sys, urllib.request

CENSUS, CACHE, OUT = sys.argv[1:4]
COUNCILS = {
    "Calderdale Metropolitan Borough Council": "calderdale",
    "Cambridgeshire Insight": "cambridgeshire",
    "London Borough of Barnet": "barnet",
}
LABEL = [r"^expense.?type$", r"^account.?description$"]
MERCH = re.compile(r"merchant.?name|^merchant$|^supplier|^vendor|^payee|^creditor", re.I)
FORMATS = ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d", "%d-%b-%y", "%d-%b-%Y", "%d %b %Y", "%d.%m.%Y", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M")


def parse_date(text):
    text = text.strip()
    for fmt in FORMATS:
        try:
            return dt.datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            pass
    return None


def parse_amount(text):
    text = re.sub(r"[£,\s]", "", text).replace("(", "-").replace(")", "")
    try:
        return round(float(text), 2)
    except ValueError:
        return None


def col(header, pattern):
    return next((i for i, c in enumerate(header) if re.search(pattern, c, re.I)), None)


def read_file(path):
    raw = open(path, "rb").read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("cp1252", "replace")
    if "<html" in text[:500].lower():
        return []
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    rows = list(csv.reader(io.StringIO(text, newline="")))
    start = next((i for i, r in enumerate(rows[:12]) if sum(bool(c.strip()) for c in r) >= 4), None)
    if start is None:
        return []
    header = [c.strip() for c in rows[start]]
    label = next((i for p in LABEL for i, c in enumerate(header) if re.search(p, c, re.I)), None)
    merchant = next((i for i, c in enumerate(header) if MERCH.search(c)), None)
    date = next((i for i, c in enumerate(header) if re.search(r"transaction.?date|^date|payment.?date|date", c, re.I)), None)
    amount = col(header, r"amount|net|value|gross|total")
    area = col(header, r"expense.?area|directorate|cost.?cent")
    category = col(header, r"merchant.?category$|merchant.?category.?desc|merchant.?desc")
    if label is None or merchant is None or date is None:
        return []
    out = []
    for r in rows[start + 1:]:
        if len(r) <= max(label, merchant, date):
            continue
        day = parse_date(r[date])
        if not (r[merchant].strip() and r[label].strip() and day):
            continue
        get = lambda i: r[i].strip() if i is not None and i < len(r) else ""
        out.append({
            "merchant": r[merchant].strip(), "label": " ".join(r[label].split()).lower(), "date": day,
            "amount": parse_amount(get(amount)), "area": get(area).lower(), "merchant_category": get(category).lower(),
        })
    return out


def urls_for(org):
    pkgs = {x["pkg"] for x in json.load(open(CENSUS))["probes"] if x["org"] == org}
    urls = []
    for name in sorted(pkgs):
        req = urllib.request.Request("https://ckan.publishing.service.gov.uk/api/action/package_show?id=" + name,
                                     headers={"User-Agent": "public-data-census/0.1 (research script)"})
        for r in json.load(urllib.request.urlopen(req, timeout=40))["result"].get("resources", []):
            if (r.get("format") or "").lower().strip(".") == "csv" or r["url"].lower().endswith(".csv"):
                urls.append(r["url"])
    return urls


def dedupe(files):
    """Keep legitimate repeats inside a file; drop copies of a file's rows in other files."""
    best = collections.Counter()
    example = {}
    for rows in files:
        counts = collections.Counter()
        for row in rows:
            key = (row["merchant"].lower(), row["label"], row["date"], row["amount"], row["area"])
            counts[key] += 1
            example[key] = row
        for key, n in counts.items():
            best[key] = max(best[key], n)
    return [example[k] for k, n in best.items() for _ in range(n)]


def tokens(text):
    return {t for t in re.findall(r"[a-z]{3,}", text.lower())}


def norm(m):
    return " ".join(re.sub(r"[^a-z& ]", " ", re.sub(r"\d+", " ", m.lower())).split()[:3])


def evaluate(rows):
    rows = sorted(rows, key=lambda r: r["date"])
    cut = rows[int(len(rows) * 0.8)]["date"]
    train = [r for r in rows if r["date"] < cut]
    test = [r for r in rows if r["date"] >= cut]
    options = sorted({r["label"] for r in train})
    rng = random.Random(0)
    majority = collections.Counter(r["label"] for r in train).most_common(1)[0][0]
    table = collections.defaultdict(collections.Counter)
    recent = {}
    for r in train:
        table[norm(r["merchant"])][r["label"]] += 1
        recent[norm(r["merchant"])] = r["label"]
    opt_tokens = {o: tokens(o) for o in options}

    def zero_shot(r):
        text = tokens(r["merchant"] + " " + r["merchant_category"])
        scored = [(len(text & t) / (len(t) or 1), rng.random(), o) for o, t in opt_tokens.items()]
        return max(scored)[2]

    n = len(test)
    seen = [r for r in test if norm(r["merchant"]) in table]
    score = lambda f, data=test: sum(f(r) == r["label"] for r in data) / max(1, len(data))
    return {
        "rows": len(rows), "train": len(train), "test": n, "test_from": cut, "options": len(options),
        "merchants": len({norm(r["merchant"]) for r in rows}),
        "random": round(1 / len(options), 3),
        "zero_shot_token_overlap": round(score(zero_shot), 3),
        "most_common_label": round(score(lambda r: majority), 3),
        "most_common_for_merchant": round(sum(table[norm(r["merchant"])].most_common(1)[0][0] == r["label"] for r in seen) / n, 3),
        "most_recent_for_merchant": round(sum(recent[norm(r["merchant"])] == r["label"] for r in seen) / n, 3),
        "merchant_seen_share": round(len(seen) / n, 3),
        "label_unseen_share": round(sum(r["label"] not in opt_tokens for r in test) / n, 3),
        "has_area": round(sum(bool(r["area"]) for r in rows) / len(rows), 3),
        "has_merchant_category": round(sum(bool(r["merchant_category"]) for r in rows) / len(rows), 3),
        "has_amount": round(sum(r["amount"] is not None for r in rows) / len(rows), 3),
    }


results = {}
for org, slug in COUNCILS.items():
    files = []
    for url in urls_for(org):
        path = os.path.join(CACHE, hashlib.sha1(url.encode()).hexdigest())
        if os.path.exists(path):
            rows = read_file(path)
            if rows:
                files.append(rows)
    total = sum(map(len, files))
    rows = dedupe(files)
    with open(os.path.join(OUT, slug + ".jsonl"), "w") as f:
        for r in sorted(rows, key=lambda r: r["date"]):
            f.write(json.dumps(r) + "\n")
    results[slug] = {"files_parsed": len(files), "rows_before_dedupe": total, **evaluate(rows)}
json.dump(results, open(os.path.join(OUT, "scoreboard.json"), "w"), indent=2)
print(json.dumps(results, indent=2))
