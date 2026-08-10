import os, json, urllib.request

KEY = open(os.path.expanduser(r"~\AppData\Local\hermes\.env")).read()
KEY = [l.split("=",1)[1].strip() for l in KEY.splitlines() if l.startswith("NOTION_API_KEY=")][0]

def api(path, body=None):
    req = urllib.request.Request("https://api.notion.com/v1/"+path,
        data=json.dumps(body).encode() if body else None, method="POST" if body else "GET")
    req.add_header("Authorization", "Bearer "+KEY)
    req.add_header("Notion-Version", "2025-09-03")
    req.add_header("Content-Type", "application/json")
    return json.load(urllib.request.urlopen(req))

def query_all(ds_id):
    out, cursor = [], None
    while True:
        body = {"page_size": 100}
        if cursor: body["start_cursor"] = cursor
        r = api(f"data_sources/{ds_id}/query", body)
        out += r.get("results", [])
        if not r.get("has_more"): break
        cursor = r["next_cursor"]
    return out

sources = {
    "syllabus":   "fff5b4bc",
    "daily_log":  "0b28732c",
    "mocks":      "a45f4878",
    "revision":   "1478336a",
    "physics":    "6d6b30d1",
    "chemistry":  "36d0ad49",
    "maths":      "a617d95a",
}
# Need full IDs for the per-subject ones; try search if short ids fail.
os.makedirs("raw", exist_ok=True)
for name, ds in sources.items():
    try:
        rows = query_all(ds)
        json.dump(rows, open(f"raw/{name}.json","w"), indent=1)
        print(name, len(rows), "rows OK")
    except Exception as e:
        print(name, "FAIL", str(e)[:120])
