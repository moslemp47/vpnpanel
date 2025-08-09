
# VPN Panel Pro (Full)

Features:
- JWT signup/login
- Plans, orders (mock payments), subscriptions
- Real provisioning to Marzban/Sanaei via configurable ENV
- Simple frontend (React + Tailwind CDN)
- SQLite + SQLAlchemy

## Run
Backend:
```
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python run.py
```
Frontend:
- Open `frontend/index.html` in your browser.

Edit `backend/.env` and set `MARZBAN_API_URL`, `MARZBAN_TOKEN`, `SANAEI_API_URL`, `SANAEI_TOKEN`.


**Update:** JWT auth enforced on orders/subscriptions. Use access token. Added /auth/me, /subscriptions, and provider usage endpoint.


## Security & Hardening Added
- Security headers middleware (X-Frame-Options, CSP, etc.)
- Rate limiting (per-IP) — default 120 req/min (configurable)
- JWT rotation with persisted refresh tokens (blacklist on logout)
- Admin-only protection for `/admin/*`
- CORS normalization from `.env`
- Basic login throttling (5 tries / 5 minutes)
- Safer frontend with token refresh flow
