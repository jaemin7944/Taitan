# taitan/infra/kis_client.py

import requests
import time
from typing import Dict


class KisClient:
    def __init__(self, app_key, app_secret, base_url):
        self.app_key = app_key
        self.app_secret = app_secret
        self.base_url = base_url

        self.access_token = None
        self.token_expired_at = 0

    # ----------------------------
    # 토큰 발급
    # ----------------------------
    def _issue_token(self):
        url = f"{self.base_url}/oauth2/tokenP"
        res = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            json={
                "grant_type": "client_credentials",
                "appkey": self.app_key,
                "appsecret": self.app_secret,
            },
            timeout=5,
        )

        # ✅ 여기 추가: 실패 시 응답 본문을 강제로 보여주기
        if res.status_code != 200:
            print("[KIS][TOKEN][ERROR] status =", res.status_code)
            print("[KIS][TOKEN][ERROR] body   =", res.text)
            res.raise_for_status()

        data = res.json()
        self.access_token = data["access_token"]
        self.token_expired_at = time.time() + int(data["expires_in"]) - 60


    # ----------------------------
    # 공통 GET
    # ----------------------------
    def get(self, path: str, tr_id: str, params: Dict):
        self._ensure_token()

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": tr_id,
            "custtype": "P",
            "tr_auth": "",
        }

        url = f"{self.base_url}{path}"
        res = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=5,
        )
        res.raise_for_status()
        return res.json()
    def _ensure_token(self):
        if not self.access_token or time.time() >= self.token_expired_at:
            self._issue_token()
