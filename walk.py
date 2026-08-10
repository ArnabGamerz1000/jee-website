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
        return {"__error": e.code, "body": e.read().decode()[:400]}

def walk(bid, depth=0):
    r = api(f"blocks/{bid}/children?page_size=100")
    for b in r.get("results", []):
        t = b["type"]
        extra = ""
        if t == "child_database": extra = b["child_database"].get("title","")
        if t == "child_page": extra = b["child_page"].get("title","")
        print("  "*depth + f"{t} {b['id']} {extra}")
        if b.get("has_children") and t not in ("child_database",):
            walk(b["id"], depth+1)

walk("115f4da1-663b-8034-8b76-d845da949186")
