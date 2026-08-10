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

def get_ds_id(db_id):
    r = api(f"databases/{db_id}")
    ds = r.get("data_sources", [])
    return ds[0]["id"] if ds else None

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

dbs = {
    "syllabus":  "ea4487a7-5fa8-45f0-b0d9-1b47ff2169a5",
    "daily_log": "facb8d26-b64a-47ef-9585-f5ee54f46bff",
    "mocks":     "9ea28899-fe49-42cd-b160-97883c092cad",
    "revision":  "1ad8bf46-6ab9-47fb-a797-00e5f5d6ddd4",
    "physics":   "6d6b30d1-3176-40a0-94bb-a0b126d216bc",
    "chemistry": "36d0ad49-2e5a-4d8a-bb2a-86cda8985a51",
    "maths":     "a617d95a-74da-44f0-949f-f0fb5e553213",
}
os.makedirs("raw", exist_ok=True)
for name, dbid in dbs.items():
    ds = get_ds_id(dbid)
    rows = query_all(ds)
    json.dump({"data_source_id": ds, "rows": rows}, open(f"raw/{name}.json","w"), indent=1)
    # print schema of first row
    if rows:
        props = rows[0]["properties"]
        print(name, len(rows), "rows | props:", ", ".join(f"{k}:{v['type']}" for k,v in props.items()))
    else:
        print(name, 0, "rows")
