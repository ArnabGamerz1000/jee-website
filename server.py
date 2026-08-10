"""JEE 2027 dashboard server: serves the static site + /api/data + /api/update (writes to Notion)."""
import os, json, time, urllib.request, urllib.error
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(ROOT, "data", "cache.json")
CACHE_TTL = 300  # seconds

def load_key():
    # env var wins (EC2/systemd), then local hermes .env
    if os.environ.get("NOTION_API_KEY"):
        return os.environ["NOTION_API_KEY"]
    env = os.path.expanduser(r"~\AppData\Local\hermes\.env")
    if not os.path.exists(env):
        env = os.path.join(ROOT, ".env")
    for line in open(env):
        if line.startswith("NOTION_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("NOTION_API_KEY not found")

KEY = load_key()

def notion(path, body=None, method=None):
    req = urllib.request.Request(
        "https://api.notion.com/v1/" + path,
        data=json.dumps(body).encode() if body is not None else None,
        method=method or ("POST" if body is not None else "GET"))
    req.add_header("Authorization", "Bearer " + KEY)
    req.add_header("Notion-Version", "2025-09-03")
    req.add_header("Content-Type", "application/json")
    return json.load(urllib.request.urlopen(req))

def get_ds_id(db_id):
    ds = notion(f"databases/{db_id}").get("data_sources", [])
    return ds[0]["id"] if ds else None

def query_all(ds_id):
    out, cursor = [], None
    while True:
        body = {"page_size": 100}
        if cursor: body["start_cursor"] = cursor
        r = notion(f"data_sources/{ds_id}/query", body)
        out += r.get("results", [])
        if not r.get("has_more"): break
        cursor = r["next_cursor"]
    return out

DB_IDS = {
    "syllabus":  "ea4487a7-5fa8-45f0-b0d9-1b47ff2169a5",
    "daily_log": "facb8d26-b64a-47ef-9585-f5ee54f46bff",
    "mocks":     "9ea28899-fe49-42cd-b160-97883c092cad",
    "revision":  "1ad8bf46-6ab9-47fb-a797-00e5f5d6ddd4",
}
# property builders for new rows
ADD_SCHEMAS = {
    "daily_log": lambda p: {
        "Day": {"title": [{"text": {"content": p["Day"]}}]},
        "Date": {"date": {"start": p["Date"]}},
        "Hours Studied": {"number": p["Hours Studied"]},
        "Questions Solved": {"number": p["Questions Solved"]},
        "Mood": {"select": {"name": p["Mood"]}} if p.get("Mood") else None,
        "Physics": {"checkbox": bool(p.get("Physics"))},
        "Chemistry": {"checkbox": bool(p.get("Chemistry"))},
        "Maths": {"checkbox": bool(p.get("Maths"))},
        "What I studied": {"rich_text": [{"text": {"content": p.get("What I studied", "")[:2000]}}]},
    },
    "mocks": lambda p: {
        "Test": {"title": [{"text": {"content": p["Test"]}}]},
        "Date": {"date": {"start": p["Date"]}},
        "Type": {"select": {"name": p["Type"]}},
        "Physics": {"number": p.get("Physics", 0)},
        "Chemistry": {"number": p.get("Chemistry", 0)},
        "Maths": {"number": p.get("Maths", 0)},
        "Total": {"number": p.get("Total", 0)},
        "Percentile est.": {"number": p["Percentile est."]} if p.get("Percentile est.") is not None else None,
        "Mistakes/Lessons": {"rich_text": [{"text": {"content": p.get("Mistakes/Lessons", "")[:2000]}}]},
    },
    "revision": lambda p: {
        "Topic": {"title": [{"text": {"content": p["Topic"]}}]},
        "Subject": {"select": {"name": p["Subject"]}},
        "Next Revision": {"date": {"start": p["Next Revision"]}},
        "Revision #": {"number": p.get("Revision #", 1)},
        "Confidence": {"select": {"name": str(p.get("Confidence", 2))}},
    },
}

def apply_update(u):
    page_id = u["id"]; field = u["field"]; value = u["value"]
    if field == "Status":
        props = {"Status": {"select": {"name": value}}}
    elif field == "Questions Solved":
        props = {"Questions Solved": {"number": int(value)}}
    elif field == "Target Date":
        props = {"Target Date": {"date": {"start": value}}}
    elif field == "__rev_done":
        props = {"Revision #": {"number": int(value["next"])},
                 "Next Revision": {"date": {"start": value["date"]}}}
    else:
        raise ValueError("field not allowed")
    notion(f"pages/{page_id}", {"properties": props}, method="PATCH")

def apply_add(u):
    db = u["db"]
    if db not in DB_IDS or db not in ADD_SCHEMAS:
        raise ValueError("unknown db")
    props = {k: v for k, v in ADD_SCHEMAS[db](u["props"]).items() if v is not None}
    notion("pages", {"parent": {"database_id": DB_IDS[db]}, "properties": props})

def txt(rt):
    return "".join(t.get("plain_text", "") for t in (rt or []))

def parse_row(p):
    pr = p["properties"]
    def sel(n):
        v = pr.get(n, {}).get("select")
        return v["name"] if v else None
    row = {"id": p["id"]}
    for name, v in pr.items():
        t = v["type"]
        if t == "title":        row[name] = txt(v["title"])
        elif t == "rich_text":  row[name] = txt(v["rich_text"])
        elif t == "select":     row[name] = v["select"]["name"] if v["select"] else None
        elif t == "number":     row[name] = v["number"]
        elif t == "checkbox":   row[name] = v["checkbox"]
        elif t == "date":       row[name] = v["date"]["start"] if v["date"] else None
    return row

def fetch_all():
    data = {"fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    for name, dbid in DB_IDS.items():
        rows = query_all(get_ds_id(dbid))
        data[name] = [parse_row(r) for r in rows]
    return data

def get_data(force=False):
    if not force and os.path.exists(CACHE) and time.time() - os.path.getmtime(CACHE) < CACHE_TTL:
        return json.load(open(CACHE))
    data = fetch_all()
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    json.dump(data, open(CACHE, "w"), indent=1)
    return data

def apply_update(u):
    page_id = u["id"]; field = u["field"]; value = u["value"]
    if field == "Status":
        props = {"Status": {"select": {"name": value}}}
    elif field == "Questions Solved":
        props = {"Questions Solved": {"number": int(value)}}
    elif field == "Target Date":
        props = {"Target Date": {"date": {"start": value}}}
    else:
        raise ValueError("field not allowed")
    notion(f"pages/{page_id}", {"properties": props}, method="PATCH")

class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *a): pass

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/data":
            force = "refresh=1" in (urlparse(self.path).query or "")
            try:
                self._json(get_data(force=force))
            except Exception as e:
                self._json({"error": str(e)}, 500)
            return
        if path == "/":
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            if path == "/api/update":
                apply_update(body)
            elif path == "/api/add":
                apply_add(body)
            else:
                self._json({"error": "not found"}, 404); return
            get_data(force=True)  # keep cache consistent after any write
            self._json({"ok": True})
        except Exception as e:
            self._json({"ok": False, "error": str(e)}, 500)

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

if __name__ == "__main__":
    import sys
    port = int(os.environ.get("PORT", "8227"))
    host = os.environ.get("HOST", "127.0.0.1")
    os.chdir(ROOT)
    if "--no-prefetch" not in sys.argv:
        print("Fetching Notion data (initial cache)...")
        get_data(force=True)
    print(f"Serving on http://{host}:{port}")
    ThreadingHTTPServer((host, port), Handler).serve_forever()
