JEE 2027 dashboard — AWS EC2 deploy guide
==========================================

WHAT YOU GET
A 6-page site (Overview / Chapters / Timeline / Daily Log / Mock Tests / Revision),
served 24/7 over HTTPS, reading your Notion dashboard every 5 min and writing
every mark (status, question counts, log entries, mock scores, revision bumps)
straight back to Notion.

--------------------------------------------------------------------------
STEP 1 — Launch the instance (AWS console, ~5 min)
--------------------------------------------------------------------------
1. EC2 → Launch instance:
   - Name: jee-dashboard
   - AMI: Ubuntu Server 24.04 LTS (free tier eligible)
   - Instance type: t3.micro (free tier)  — 750 hrs/month free for 12 months
   - Key pair: create one, download the .pem
2. Network settings → create security group with inbound rules:
     SSH    22   My IP
     HTTP   80   0.0.0.0/0     (needed for HTTPS cert)
     HTTPS  443  0.0.0.0/0
3. Launch. Then: EC2 → Elastic IPs → Allocate → Associate with the instance
   (so your IP never changes; free while attached to a running instance).

--------------------------------------------------------------------------
STEP 2 — Point a name at it
--------------------------------------------------------------------------
Cheapest: use a free subdomain of a domain you own, or buy any cheap one
(~₹80/yr). Add an A record:  jee.yourdomain.com → <your Elastic IP>.
(Without a domain you can still use HTTP on the Elastic IP — tell me and I'll
give you the variant without Caddy/HTTPS.)

--------------------------------------------------------------------------
STEP 3 — Upload + install (from this PC)
--------------------------------------------------------------------------
In git-bash here (I can run these for you once the instance exists):

  cd ~/jee-website
  tar czf ../jee-website.tar.gz --exclude=data/cache.json --exclude=raw .
  scp -i ~/Downloads/YOURKEY.pem ../jee-website.tar.gz ubuntu@<ELASTIC-IP>:~
  scp -i ~/Downloads/YOURKEY.pem deploy-ec2.sh ubuntu@<ELASTIC-IP>:~
  ssh -i ~/Downloads/YOURKEY.pem ubuntu@<ELASTIC-IP>

On the instance:
  chmod +x deploy-ec2.sh
  DOMAIN=jee.yourdomain.com ./deploy-ec2.sh 'ntn_YOUR_NOTION_KEY'

Done — https://jee.yourdomain.com is live, open to anyone with the link.
(The old basic-auth password gate was removed on 2026-08-10. If you ever want
it back, add a basicauth block to /etc/caddy/Caddyfile and reload caddy.)

--------------------------------------------------------------------------
OPERATIONS CHEAT-SHEET
--------------------------------------------------------------------------
  journalctl -u jee -f          live app logs
  sudo systemctl restart jee    restart app
  curl localhost:8227/api/data?refresh=1    force a Notion re-sync
Data cache: /opt/jee-website/data/cache.json (auto-refreshes every 5 min,
and immediately after any write you make from the site).

COST: $0 within free tier (t3.micro 750h/mo + 30GB disk + 1 Elastic IP on a
running instance). After 12 months: ~$8/mo, or just stop the instance when
JEE is over.
