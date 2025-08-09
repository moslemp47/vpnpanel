#!/usr/bin/env bash
set -euo pipefail

# ================================
# VPN Panel Pro — One-click Installer
# OS: Ubuntu 20.04+/22.04+, Debian 11+
# Example:
#   bash <(curl -fsSL https://raw.githubusercontent.com/USER/REPO/main/scripts/install.sh) \
#     --repo https://github.com/USER/REPO.git --branch main
# With domain + HTTPS:
#   ... --domain panel.example.com --enable-https --email you@example.com
# ================================

# ---------- Config (overridable by flags or env) ----------
REPO_URL="${REPO_URL:-}"
REPO_BRANCH="${REPO_BRANCH:-main}"
INSTALL_DIR="${INSTALL_DIR:-/opt/vpnpanel}"
SYSTEM_USER="${SYSTEM_USER:-vpnpanel}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
BACKEND_HOST="127.0.0.1"
BACKEND_PORT="${BACKEND_PORT:-8000}"
DOMAIN="${DOMAIN:-}"
ENABLE_HTTPS="${ENABLE_HTTPS:-false}"
EMAIL="${EMAIL:-}"

# ---------- Helpers ----------
log() { echo -e "\033[1;36m[+] $*\033[0m"; }
err() { echo -e "\033[1;31m[!] $*\033[0m" >&2; }
need() { command -v "$1" >/dev/null 2>&1 || { err "Missing $1"; exit 1; }; }

usage() {
  cat <<EOF
VPN Panel Pro Installer
Flags:
  --repo URL            Git repo (required) e.g. https://github.com/USER/REPO.git
  --branch BR           Git branch (default: main)
  --install-dir PATH    Install path (default: /opt/vpnpanel)
  --user NAME           System user to run service (default: vpnpanel)
  --domain DOMAIN       Public domain for nginx (optional)
  --enable-https        Enable Let's Encrypt via certbot (requires --domain and --email)
  --email you@example.com
Examples:
  bash <(curl -fsSL https://raw.githubusercontent.com/USER/REPO/main/scripts/install.sh) \\
    --repo https://github.com/USER/REPO.git --branch main
  bash <(curl -fsSL https://raw.githubusercontent.com/USER/REPO/main/scripts/install.sh) \\
    --repo https://github.com/USER/REPO.git --branch main --domain panel.example.com --enable-https --email you@example.com
EOF
}

# ---------- Parse flags ----------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo) REPO_URL="$2"; shift 2;;
    --branch) REPO_BRANCH="$2"; shift 2;;
    --install-dir) INSTALL_DIR="$2"; shift 2;;
    --user) SYSTEM_USER="$2"; shift 2;;
    --domain) DOMAIN="$2"; shift 2;;
    --enable-https) ENABLE_HTTPS="true"; shift 1;;
    --email) EMAIL="$2"; shift 2;;
    -h|--help) usage; exit 0;;
    *) err "Unknown option: $1"; usage; exit 1;;
  esac
done

if [[ -z "${REPO_URL}" ]]; then
  err "--repo is required (e.g. --repo https://github.com/USER/REPO.git)"
  exit 1
fi

# ---------- Pre-flight ----------
need apt-get
log "Updating system & installing base packages..."
sudo apt-get update -y
sudo apt-get install -y git curl unzip ca-certificates nginx python3 python3-venv python3-pip sqlite3

# ---------- System user & folders ----------
log "Ensuring system user: ${SYSTEM_USER}"
if ! id -u "${SYSTEM_USER}" >/dev/null 2>&1; then
  sudo useradd -r -m -d "${INSTALL_DIR}" -s /usr/sbin/nologin "${SYSTEM_USER}" || true
fi
sudo mkdir -p "${INSTALL_DIR}"
sudo chown -R "${SYSTEM_USER}:${SYSTEM_USER}" "${INSTALL_DIR}"

# ---------- Fetch code ----------
log "Fetching code from ${REPO_URL} (branch: ${REPO_BRANCH})"
if [[ -d "${INSTALL_DIR}/src/.git" ]]; then
  sudo -u "${SYSTEM_USER}" git -C "${INSTALL_DIR}/src" fetch --all
  sudo -u "${SYSTEM_USER}" git -C "${INSTALL_DIR}/src" checkout "${REPO_BRANCH}"
  sudo -u "${SYSTEM_USER}" git -C "${INSTALL_DIR}/src" pull --ff-only origin "${REPO_BRANCH}"
else
  sudo -u "${SYSTEM_USER}" git clone --branch "${REPO_BRANCH}" --depth 1 "${REPO_URL}" "${INSTALL_DIR}/src"
fi

# ---------- Backend setup ----------
log "Setting up backend virtualenv & dependencies..."
sudo -u "${SYSTEM_USER}" bash -c "cd '${INSTALL_DIR}/src/backend' && ${PYTHON_BIN} -m venv .venv"
sudo -u "${SYSTEM_USER}" bash -c "source '${INSTALL_DIR}/src/backend/.venv/bin/activate' && pip install --upgrade pip && pip install -r '${INSTALL_DIR}/src/backend/requirements.txt'"

# Create .env if missing
if [[ ! -f "${INSTALL_DIR}/src/backend/.env" ]]; then
  log "Creating backend .env from example & generating secrets..."
  sudo -u "${SYSTEM_USER}" cp "${INSTALL_DIR}/src/backend/.env.example" "${INSTALL_DIR}/src/backend/.env"
  ACCESS_SECRET="$(head -c 32 /dev/urandom | base64)"
  JWT_SECRET="$(head -c 32 /dev/urandom | base64)"
  sudo -u "${SYSTEM_USER}" bash -c "sed -i \"s|APP_SECRET=.*|APP_SECRET=${ACCESS_SECRET}|g\" '${INSTALL_DIR}/src/backend/.env'"
  sudo -u "${SYSTEM_USER}" bash -c "sed -i \"s|JWT_SECRET=.*|JWT_SECRET=${JWT_SECRET}|g\" '${INSTALL_DIR}/src/backend/.env'"
  if [[ -n "${DOMAIN}" ]]; then
    sudo -u "${SYSTEM_USER}" bash -c "sed -i \"s|CORS_ORIGINS=.*|CORS_ORIGINS=http://${DOMAIN},https://${DOMAIN}|g\" '${INSTALL_DIR}/src/backend/.env'"
  fi
fi

# ---------- Patch frontend API to /api (via nginx proxy) ----------
log "Patching frontend to use '/api' proxy..."
sudo sed -i 's|const API = ".*";|const API = "/api";|' "${INSTALL_DIR}/src/frontend/index.html" || true

# ---------- systemd service ----------
log "Installing systemd service..."
SERVICE_FILE="/etc/systemd/system/vpnpanel-backend.service"
sudo bash -c "cat > '${SERVICE_FILE}'" <<UNIT
[Unit]
Description=VPN Panel Pro Backend (FastAPI)
After=network.target

[Service]
Type=simple
User=${SYSTEM_USER}
WorkingDirectory=${INSTALL_DIR}/src/backend
Environment=PATH=${INSTALL_DIR}/src/backend/.venv/bin
ExecStart=${INSTALL_DIR}/src/backend/.venv/bin/uvicorn app.main:app --host ${BACKEND_HOST} --port ${BACKEND_PORT}
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT

sudo systemctl daemon-reload
sudo systemctl enable vpnpanel-backend
sudo systemctl restart vpnpanel-backend

# ---------- nginx ----------
log "Configuring nginx (static frontend + /api -> backend)"
SITE_CONF="/etc/nginx/sites-available/vpnpanel.conf"
sudo bash -c "cat > '${SITE_CONF}'" <<NGINX
server {
    listen 80;
    server_name ${DOMAIN:-_};

    root ${INSTALL_DIR}/src/frontend;
    index index.html;

    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

    # Proxy API to FastAPI
    location /api/ {
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_pass http://${BACKEND_HOST}:${BACKEND_PORT}/;
    }

    # SPA fallback
    location / {
        try_files \$uri /index.html;
    }
}
NGINX

sudo ln -sf "${SITE_CONF}" /etc/nginx/sites-enabled/vpnpanel.conf
sudo rm -f /etc/nginx/sites-enabled/default || true
sudo nginx -t
sudo systemctl restart nginx

# ---------- HTTPS (optional) ----------
if [[ "${ENABLE_HTTPS}" == "true" ]]; then
  if [[ -z "${DOMAIN}" || -z "${EMAIL}" ]]; then
    err "ENABLE_HTTPS=true needs --domain and --email"
  else
    log "Installing certbot & issuing certificate for ${DOMAIN}..."
    sudo apt-get install -y certbot python3-certbot-nginx
    sudo certbot --nginx -d "${DOMAIN}" --non-interactive --agree-tos -m "${EMAIL}" --redirect || true
  fi
fi

log "Done!"
echo "---------------------------------------------"
if [[ -n "${DOMAIN}" ]]; then
  echo "Frontend:  http://${DOMAIN}  (or https if enabled)"
  echo "API:       http://${DOMAIN}/api"
else
  echo "Frontend:  http://YOUR_SERVER_IP"
  echo "API:       http://YOUR_SERVER_IP/api"
fi
echo "Service:   vpnpanel-backend (systemctl status/restart vpnpanel-backend)"
echo "Install:   ${INSTALL_DIR}"
