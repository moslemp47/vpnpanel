#!/usr/bin/env bash
set -euo pipefail
SERVICE=vpnpanel-backend
INSTALL_DIR=${INSTALL_DIR:-/opt/vpnpanel}

echo "[*] Stopping and disabling service..."
sudo systemctl stop "$SERVICE" || true
sudo systemctl disable "$SERVICE" || true
sudo rm -f /etc/systemd/system/${SERVICE}.service
sudo systemctl daemon-reload

echo "[*] Removing nginx site..."
sudo rm -f /etc/nginx/sites-enabled/vpnpanel.conf
sudo rm -f /etc/nginx/sites-available/vpnpanel.conf
sudo systemctl restart nginx || true

echo "[*] Removing app files..."
sudo rm -rf "${INSTALL_DIR}"

echo "Uninstalled."
