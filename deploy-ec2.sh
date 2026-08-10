#!/usr/bin/env bash
# Deploy JEE 2027 dashboard on a fresh Ubuntu EC2 (run ON the instance).
# Usage:  ./deploy-ec2.sh 'ntn_YOUR_NOTION_KEY'
set -euo pipefail

KEY="${1:?pass your NOTION_API_KEY as the first argument}"
APP=/opt/jee-website

sudo apt-get update -y
sudo apt-get install -y python3 caddy

# app files (upload the bundle to ~ first: scp -i key.pem jee-website.tar.gz ubuntu@IP:~)
sudo mkdir -p "$APP"
sudo tar xzf ~/jee-website.tar.gz -C "$APP"
echo "NOTION_API_KEY=$KEY" | sudo tee "$APP/.env" >/dev/null
sudo chmod 600 "$APP/.env"

# systemd service — runs 24/7, restarts on crash/reboot
sudo tee /etc/systemd/system/jee.service >/dev/null <<EOF
[Unit]
Description=JEE 2027 dashboard
After=network-online.target
[Service]
WorkingDirectory=$APP
Environment=HOST=127.0.0.1 PORT=8227
ExecStart=/usr/bin/python3 $APP/server.py
Restart=always
RestartSec=3
[Install]
WantedBy=multi-user.target
EOF
sudo systemctl enable --now jee

# Caddy -> automatic HTTPS on your domain; reverse-proxies to the app
sudo tee /etc/caddy/Caddyfile >/dev/null <<EOF
${DOMAIN:-jee.example.com} {
    reverse_proxy 127.0.0.1:8227
}
EOF
sudo systemctl reload caddy

echo "Done. Open https://${DOMAIN:-jee.example.com} (no login required)"
echo "Check:  sudo systemctl status jee   |   journalctl -u jee -f"
