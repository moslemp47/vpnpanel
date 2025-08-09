import requests
from ..config import settings

class MarzbanClient:
    def __init__(self):
        self.base = settings.MARZBAN_API_URL
        self.token = settings.MARZBAN_TOKEN

    def _headers(self):
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    def create_user(self, username: str, password: str, quota_gb: float, days: int) -> dict:
        if not self.base:
            return {"error": "MARZBAN_API_URL not set"}
        payload = {"username": username, "password": password, "quota_gb": quota_gb, "days": days}
        try:
            r = requests.post(f"{self.base.rstrip('/')}/users", json=payload, headers=self._headers(), timeout=15)
            return r.json()
        except Exception as e:
            return {"error": str(e)}
