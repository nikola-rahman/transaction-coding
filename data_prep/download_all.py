"""Resumable download of public payment records, needed fields only, stored as gzipped pages."""
import gzip, json, os, sys, time, urllib.parse, urllib.request

OUT, PAGE = sys.argv[1], 50000
UA = {"User-Agent": "public-data-research/0.1 (research script)", "Accept-Encoding": "gzip"}
SOURCES = [
    ("ct", "data.ct.gov", "wijb-dc4k", ["organization", "vendor_name", "expense_description", "date", "amount"], 77069),
    ("fulton", "data.fultoncountyga.gov", "mxhc-krcg", ["vendor_legal_name", "object_name", "disb_date", "amount", "department_name"], 232722),
    ("ramsey", "data.ramseycountymn.gov", "4htu-nawa", ["supplier_name", "account_name", "payment_date", "amount", "department_name", "description"], 2193741),
    ("la", "controllerdata.lacity.org", "pggv-e4fn", ["vendor_name", "account_name", "account_code", "transaction_date", "dollar_amount", "department_name", "description"], 6615359),
]


def fetch(url):
    for attempt in range(8):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300) as r:
                data = r.read()
                return data if r.headers.get("Content-Encoding") == "gzip" else gzip.compress(data)
        except Exception as e:
            code = getattr(e, "code", 0)
            print("retry", type(e).__name__, code, flush=True)
            if code in (401, 403):
                raise
            time.sleep(min(15 * (attempt + 1), 120))
    raise RuntimeError("giving up on " + url)


for name, host, did, cols, total in SOURCES:
    folder = os.path.join(OUT, name); os.makedirs(folder, exist_ok=True)
    for offset in range(0, total + PAGE, PAGE):
        path = os.path.join(folder, f"{offset:09d}.json.gz")
        if os.path.exists(path):
            continue
        query = urllib.parse.urlencode({"$select": ",".join(cols), "$limit": PAGE, "$offset": offset, "$order": ":id"})
        data = fetch(f"https://{host}/resource/{did}.json?{query}")
        rows = len(json.loads(gzip.decompress(data)))
        if rows == 0:
            break
        with open(path + ".tmp", "wb") as f:
            f.write(data)
        os.rename(path + ".tmp", path)
        print(name, offset + rows, f"{len(data) / 1e6:.1f}MB", flush=True)
        time.sleep(1)
print("DOWNLOAD DONE", flush=True)
