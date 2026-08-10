import os, json, urllib.request

KEY = open(os.path.expanduser(r"~\AppData\Local\hermes\.env")).read()
KEY = [l.split("=",1)[1].strip() for l in KEY.splitlines() if l.startswith("NOTION_API_KEY=")][0]

def api(path, body=None):
    req = urllib.request.Request("https://api.notion.com/v1/"+path,
        data=json.dumps(body).encode() if body else None, method="POST" if body else "GET")
    req.add_header("Authorization", "Bearer "+KEY)
    req.add_header("Notion-Version", "2025-09-03")
    req.add_header("Content-Type", "application/json")
    try:
        return json.load(urllib.request.urlopen(req))
    except urllib.error.HTTPError as e:
        return {"__error": e.code, "body": e.read().decode()[:500]}

r = api("search", {"page_size": 100})
for o in r.get("results", []):
    if o.get("object") in ("database","data_source"):
        title = ""
        if o.get("title"): title = "".join(t.get("plain_text","") for t in o["title"])
        print(o["object"], o["id"], "| ds:", o.get("data_sources",[{}])[0].get("id") if o.get("data_sources") else "-", "|", title)
