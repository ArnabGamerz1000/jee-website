#!/usr/bin/env python3
"""JEE 2027 weekly report generator — runs on the EC2 via cron.
Fetches the dashboard's own API, computes the week, renders HTML to reports/."""
import json, os, sys, urllib.request, base64
from datetime import date, datetime, timedelta

BASE = "https://3.0.233.162.nip.io"
AUTH = "Basic " + base64.b64encode(b"arnab:jee2027arnab").decode()
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
STATUSES_DONE = {"Mastered", "Practice Done"}

def fetch():
    req = urllib.request.Request(BASE + "/api/data?refresh=1")
    req.add_header("Authorization", AUTH)
    return json.load(urllib.request.urlopen(req, timeout=60))

def d(s):
    return datetime.strptime(s, "%Y-%m-%d").date() if s else None

def esc(s):
    return (str(s or "")).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def main():
    data = fetch()
    today = date.today()
    week_start = today - timedelta(days=6)

    ch = data.get("syllabus", [])
    logs = [l for l in data.get("daily_log", []) if d(l.get("Date")) and week_start <= d(l["Date"]) <= today]
    mocks = [m for m in data.get("mocks", []) if d(m.get("Date")) and week_start <= d(m["Date"]) <= today]
    rev = data.get("revision", [])

    hrs = sum(l.get("Hours Studied") or 0 for l in logs)
    qs = sum(l.get("Questions Solved") or 0 for l in logs)
    days_logged = len(logs)
    subj_days = {s: sum(1 for l in logs if l.get(s)) for s in ("Physics","Chemistry","Maths")}

    mastered = [c for c in ch if c.get("Status") == "Mastered"]
    practice = [c for c in ch if c.get("Status") == "Practice Done"]
    overdue = [c for c in ch if d(c.get("Target Date")) and d(c["Target Date"]) < today
               and c.get("Status") not in STATUSES_DONE]
    overdue.sort(key=lambda c: c["Target Date"])
    due_next7 = [c for c in ch if d(c.get("Target Date")) and today <= d(c["Target Date"]) <= today + timedelta(days=7)
                 and c.get("Status") not in STATUSES_DONE]
    due_next7.sort(key=lambda c: c["Target Date"])
    rev_due = [r for r in rev if d(r.get("Next Revision")) and d(r["Next Revision"]) <= today + timedelta(days=7)]
    rev_due.sort(key=lambda r: r["Next Revision"] or "")

    coverage = round(100 * len([c for c in ch if c.get("Status") in STATUSES_DONE]) / max(1, len(ch)))

    # the one honest line
    notes = []
    if days_logged <= 3: notes.append(f"Only {days_logged}/7 days logged — even a bad day deserves a log entry.")
    if hrs < 45: notes.append(f"{hrs:.0f}h this week is below your ~70h drop-year pace.")
    for s, n in subj_days.items():
        if n == 0 and days_logged >= 4: notes.append(f"{s} untouched all week — retention decays fast.")
    if overdue: notes.append(f"{len(overdue)} chapters slipped their target date; the oldest is {esc(overdue[0]['Chapter'])}.")
    if not notes: notes.append("Solid week. Hold the line; do it again.")
    coaching = " ".join(notes[:3])

    def card(num, lbl, color="var(--accent)"):
        return f'<div class="card"><div class="num" style="color:{color}">{num}</div><div class="lbl">{lbl}</div></div>'

    ICON = {"Physics":"⚛️","Chemistry":"🧪","Maths":"📐"}
    def row(c, datekey="Target Date"):
        return (f'<div class="row"><span class="chip {c.get("Subject")}">{ICON.get(c.get("Subject"),"")} {esc(c.get("Subject"))}</span>'
                f'<span class="nm">{esc(c.get("Chapter") or c.get("Topic"))}</span>'
                f'<span class="dt">{esc(c.get(datekey))}</span></div>')

    html = f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Week Report · {week_start} → {today}</title>
<meta http-equiv="refresh" content="900">
<style>
body{{background:#0b0e14;color:#e6e9f0;font:14px/1.55 system-ui,sans-serif;max-width:860px;margin:0 auto;padding:28px 18px 60px}}
h1{{font-size:20px}} h1 em{{font-style:normal;color:#6c8cff}} h2{{font-size:14px;margin:26px 0 10px;color:#8b93a7;text-transform:uppercase;letter-spacing:.8px}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:12px}}
.card{{background:#12161f;border:1px solid #232a3a;border-radius:12px;padding:14px}}
.num{{font-size:24px;font-weight:700}} .lbl{{font-size:11px;color:#8b93a7}}
.row{{display:flex;gap:10px;align-items:center;background:#12161f;border:1px solid #232a3a;border-radius:10px;padding:8px 12px;margin-bottom:6px}}
.nm{{flex:1}} .dt{{color:#8b93a7;font-size:12px}}
.chip{{font-size:11px;padding:2px 9px;border-radius:99px;white-space:nowrap}}
.chip.Physics{{background:rgba(90,162,255,.15);color:#5aa2ff}} .chip.Chemistry{{background:rgba(74,222,128,.15);color:#4ade80}} .chip.Maths{{background:rgba(192,132,252,.15);color:#c084fc}}
.coach{{background:#171c28;border-left:3px solid #6c8cff;border-radius:8px;padding:14px 16px;font-size:14px}}
a{{color:#6c8cff}} .meta{{color:#8b93a7;font-size:12px}}
.mockrow{{display:flex;gap:12px;align-items:baseline;background:#12161f;border:1px solid #232a3a;border-radius:10px;padding:9px 12px;margin-bottom:6px}}
.tot{{font-size:18px;font-weight:700;color:#4ade80}}
</style></head><body>
<h1><em>JEE 2027</em> · Week Report</h1>
<div class="meta">{week_start.strftime('%d %b')} → {today.strftime('%d %b %Y')} · generated {datetime.now().strftime('%d %b, %H:%M')} · <a href="../index.html">← dashboard</a></div>

<h2>Week in numbers</h2>
<div class="cards">
 {card(f"{hrs:.1f}h", "study hours")}
 {card(f"{days_logged}/7", "days logged", "#4ade80" if days_logged>=6 else "#fbbf24")}
 {card(qs, "questions solved")}
 {card(str(coverage)+"%", "syllabus coverage")}
 {card(len(mastered), "chapters mastered")}
 {card(len(mocks), "mocks this week")}
 {card(len(overdue), "overdue chapters", "#f87171" if overdue else "#4ade80")}
</div>

<h2>Subject balance (days touched)</h2>
<div class="cards">
 {card(f'{subj_days["Physics"]}/7', "⚛️ Physics", "#5aa2ff")}
 {card(f'{subj_days["Chemistry"]}/7', "🧪 Chemistry", "#4ade80")}
 {card(f'{subj_days["Maths"]}/7', "📐 Maths", "#c084fc")}
</div>

<h2>Mocks this week</h2>
{"".join(f'<div class="mockrow"><span>{esc(m.get("Test"))}</span><span class="meta">{esc(m.get("Type") or "")}</span><span class="tot" style="margin-left:auto">{m.get("Total","—")}</span><span class="meta">P {m.get("Physics","—")} · C {m.get("Chemistry","—")} · M {m.get("Maths","—")}</span></div>' for m in mocks) or '<div class="meta">No mocks logged this week.</div>'}

<h2>Slipped / overdue ({len(overdue)})</h2>
{"".join(row(c) for c in overdue[:10]) or '<div class="meta">Nothing overdue. 🔥</div>'}

<h2>Due in the next 7 days ({len(due_next7)})</h2>
{"".join(row(c) for c in due_next7[:10]) or '<div class="meta">No chapter deadlines in the next week.</div>'}

<h2>Revision queue (next 7 days)</h2>
{"".join(row(r, "Next Revision") for r in rev_due[:10]) or '<div class="meta">Revision queue empty.</div>'}

<h2>The honest line</h2>
<div class="coach">{coaching}</div>

<p class="meta" style="margin-top:30px">Auto-generated every Sunday 21:00 IST by the server · archive: reports/report-YYYY-MM-DD.html</p>
</body></html>"""

    os.makedirs(OUT, exist_ok=True)
    name = f"report-{today.isoformat()}.html"
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
        f.write(html)
    latest = os.path.join(OUT, "latest.html")
    if os.path.islink(latest) or os.path.exists(latest):
        os.remove(latest)
    try:
        os.symlink(name, latest)
    except OSError:
        with open(latest, "w", encoding="utf-8") as f:
            f.write(html)
    print(f"Wrote {name}: {hrs:.0f}h, {days_logged}/7 days, {qs} Qs, {len(overdue)} overdue, coverage {coverage}%")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"REPORT FAILED: {e}", file=sys.stderr)
        sys.exit(1)
