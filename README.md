# JEE 2027 — Drop-Year Command Center

A personal study dashboard for JEE Mains 2027 (Session 1: Jan 22, 2027). Tracks all 83 chapters across Physics, Chemistry and Maths, daily study hours, mock test scores, and revision — with two-way sync to Notion as the database.

Live site: https://3.0.233.162.nip.io (self-hosted on AWS EC2)

## Features

- **Overview** — syllabus coverage %, chapters mastered / in progress / not started, questions solved, 7-day study hours, mocks taken. Every stat card has a hover tooltip with the underlying detail (e.g. hover "in progress" to see exactly which chapters and their statuses).
- **Chapters** — full syllabus table, click-to-update status, weightage, target dates, questions solved. Changes write straight back to Notion.
- **Timeline** — chapters laid out against target dates with overdue highlighting.
- **Daily Log** — hours studied per day, synced to a Notion database.
- **Mock Tests** — P/C/M/total scores per test, score progression sparkline, best/average stats, mistakes log.
- **Revision** — spaced-repetition style list of chapters due for a revisit.
- **Weekly report** — auto-generated HTML report (cron on the server) summarizing the week.
- **Instant navigation** — pages paint immediately from a localStorage cache and revalidate against the server in the background; smooth fade transitions between pages.
- **Motivation** — press `Q` anywhere for a fullscreen quote.

## Architecture

```
Browser (static HTML/CSS/JS)
    │  GET /api/data          POST /api/update · POST /api/add
    ▼
server.py  (Python stdlib http.server, port 8227)
    │  5-min local cache (data/cache.json)
    ▼
Notion API  (4 databases: syllabus, daily log, mocks, revision)
```

- **No frameworks, no build step.** Frontend is hand-written HTML + one shared `js/common.js` (store, layout shell, helpers). Styling is a single `style.css`.
- **No application database.** Notion is the source of truth; the server caches responses for 5 minutes and the browser caches the last-known dataset in localStorage for instant paint.
- Chapter statuses: `Not Started → Theory Started → Theory Done → Practice Started → Practice Done → Mastered`, plus `Needs Revision`.

## File map

| Path | Purpose |
|---|---|
| `index.html` | Overview page (stat cards + hover tooltips, next-up list, phase plan) |
| `chapters.html` | Full syllabus table with inline status editing |
| `timeline.html` | Chapters by target date |
| `log.html` | Daily study log |
| `mocks.html` | Mock test entry + history + progression |
| `revision.html` | Revision queue |
| `js/common.js` | Shared store (Notion sync, cache, revalidation), layout shell, helpers |
| `style.css` | All styling, incl. card tooltips and page transitions |
| `server.py` | Static file server + `/api/data`, `/api/update`, `/api/add` + Notion cache |
| `report.py` | Weekly report generator (runs via cron on the server) |
| `fetch.py` / `fetch2.py` / `search.py` / `walk.py` | One-off Notion API exploration/maintenance scripts |
| `raw/` | Raw Notion dumps (reference snapshots) |
| `deploy-ec2.sh` | One-shot provisioning script for a fresh Ubuntu EC2 |
| `DEPLOY-AWS.md` | Step-by-step AWS deployment notes |

## Running locally

```bash
export NOTION_API_KEY=ntn_...   # or put it in .env next to server.py
python server.py                # serves on http://127.0.0.1:8227
```

## Deployment (AWS EC2)

The app runs as a systemd service (`jee`) behind Caddy (automatic HTTPS):

```bash
# on your machine
tar czf jee-website.tar.gz .
scp -i key.pem jee-website.tar.gz ubuntu@<EC2_IP>:~

# on the EC2 instance
./deploy-ec2.sh 'ntn_YOUR_NOTION_KEY'
```

See `DEPLOY-AWS.md` for the full walkthrough (Elastic IP, security groups, Caddy domain config).

Day-to-day updates are just file copies — no restart needed for HTML/CSS/JS:

```bash
scp -i key.pem index.html style.css js/common.js ubuntu@<EC2_IP>:/tmp/
ssh -i key.pem ubuntu@<EC2_IP> 'sudo cp /tmp/index.html /tmp/style.css /opt/jee-website/ && sudo cp /tmp/common.js /opt/jee-website/js/'
```

## Phase plan (built into the dashboard)

1. **Coverage** (Aug 10 – Oct 31) — all High+Medium chapters to ≥ Practice Done
2. **Application** (Nov 1 – Dec 31) — PYQs, part tests, 1→2 full tests/week
3. **Simulation** (Jan 1 – Jan 21) — full mock every 2 days, revision only
