import requests
import json
import uuid
from datetime import datetime, timedelta
from PySide6.QtCore import QObject, Signal, QTimer
from config import KIS_APP_KEY, KIS_APP_SECRET, CANO, ACNT_PRDT_CD, KIS_API_BASE_URL



class KisApiManager(QObject):
    token_updated = Signal(str)
    price_fetched = Signal(str, float, float)
    buy_order_sent = Signal(str, float, int)
    sell_order_sent = Signal(str, float, int)
    api_error = Signal(str)
    balance_updated = Signal(list, list, dict)

    def __init__(self):
        super().__init__()
        self.access_token = None
        self.token_expiry_time = None
        self.headers = {
            "Content-Type": "application/json; utf-8",
            "Accept": "text/json",
            "appkey": KIS_APP_KEY,
            "appsecret": KIS_APP_SECRET
        }
        self.get_access_token()

        self.token_renewal_timer = QTimer()
        self.token_renewal_timer.timeout.connect(self.get_access_token)
        self.token_renewal_timer.start(23 * 60 * 60 * 1000 + 50 * 60 * 1000)  # 23시간 50분마다 갱신

    def get_access_token(self):
        url = f"{KIS_API_BASE_URL}/oauth2/tokenP"
        body = {
            "grant_type": "client_credentials",
            "appkey": KIS_APP_KEY,
            "appsecret": KIS_APP_SECRET
        }
        try:
            res = requests.post(url, data=json.dumps(body), headers=self.headers)
            res.raise_for_status()
            res_data = res.json()
            if res_data.get("access_token"):
                self.access_token = res_data["access_token"]
                self.headers["Authorization"] = f"Bearer {self.access_token}"
                self.token_expiry_time = datetime.now() + timedelta(seconds=int(res_data.get("expires_in", 86400)))
                self.token_updated.emit("액세스 토큰 갱신 완료")
            else:
                self.api_error.emit(res_data.get("msg1", "토큰 발급 실패"))
        except Exception as e:
            self.api_error.emit(f"[토큰 오류] {str(e)}")

    def _send_request(self, method, path, headers_ext=None, data=None, params=None):
        if not self.access_token:
            self.get_access_token()
            return None

        req_headers = self.headers.copy()
        if headers_ext:
            req_headers.update(headers_ext)

        try:
            url = f"{KIS_API_BASE_URL}{path}"
            if method == "GET":
                response = requests.get(url, headers=req_headers, params=params)
            elif method == "POST":
                response = requests.post(url, headers=req_headers, data=json.dumps(data) if data else None)
            else:
                raise ValueError("지원하지 않는 HTTP 메서드")

            response.raise_for_status()
            return response.json()

        except Exception as e:
            self.api_error.emit(f"[API 요청 오류] {str(e)}")
            return None

    def get_overseas_current_price(self, ticker):
        headers_ext = {
            "tr_id": "FHKST01010100",
            "custtype": "P"
        }
        params = {
            "AUTH": "",
            "EXCD": "NAS",
            "SYMB": ticker
        }
        data = self._send_request("GET", "/uapi/overseas-price/v1/quotations/overseas-price", headers_ext, params=params)
        if data and data.get("rt_cd") == "0":
            output = data["output"]
            try:
                current_price = float(output.get("last", 0))
                previous_close = float(output.get("base", 0))
                change_percent = ((current_price - previous_close) / previous_close) * 100 if previous_close else 0.0
                self.price_fetched.emit(ticker, round(change_percent, 2), current_price)
                return round(change_percent, 2), current_price
            except:
                self.api_error.emit(f"가격 데이터 파싱 오류: {output}")
        else:
            self.api_error.emit(f"{ticker} 시세 조회 실패")
        return 0.0, None

    def send_overseas_buy_order(self, ticker, price, quantity):
        headers_ext = {
            "tr_id": "TTTC0802U",
            "custtype": "P",
            "gt_uid": str(uuid.uuid4())
        }
        data = {
            "CANO": CANO,
            "ACNT_PRDT_CD": ACNT_PRDT_CD,
            "OVRS_EXCG_CD": "NAS",
            "PDNO": ticker,
            "ORD_UNPR": str(price),
            "ORD_QTY": str(quantity),
            "SLL_BUY_DVSN_CD": "01",
            "ORD_DVSN_CD": "00"
        }
        res = self._send_request("POST", "/uapi/overseas-stock/v1/trading/order", headers_ext, data)
        if res and res.get("rt_cd") == "0":
            self.buy_order_sent.emit(ticker, price, quantity)
            return True
        self.api_error.emit(f"매수 실패: {res.get('msg1', '') if res else '응답 없음'}")
        return False

    def send_overseas_sell_order(self, ticker, price, quantity):
        headers_ext = {
            "tr_id": "TTTC0801U",
            "custtype": "P",
            "gt_uid": str(uuid.uuid4())
        }
        data = {
            "CANO": CANO,
            "ACNT_PRDT_CD": ACNT_PRDT_CD,
            "OVRS_EXCG_CD": "NAS",
            "PDNO": ticker,
            "ORD_UNPR": str(price),
            "ORD_QTY": str(quantity),
            "SLL_BUY_DVSN_CD": "02",
            "ORD_DVSN_CD": "00"
        }
        res = self._send_request("POST", "/uapi/overseas-stock/v1/trading/order", headers_ext, data)
        if res and res.get("rt_cd") == "0":
            self.sell_order_sent.emit(ticker, price, quantity)
            return True
        self.api_error.emit(f"매도 실패: {res.get('msg1', '') if res else '응답 없음'}")
        return False

    def get_overseas_balance(self):
        headers_ext = {
            "tr_id": "CTRP6504R",
            "custtype": "P"
        }
        params = {
            "CANO": CANO,
            "ACNT_PRDT_CD": ACNT_PRDT_CD,
            "OVRS_EXCG_CD": "NAS",
            "TR_CRCY_CD": "USD",
            "INQR_DVSN_CD": "00",
            "WCRC_FRCR_DVSN_CD": "02",
            "TR_MKET_CD": "01",
            "NATN_CD": "840"
        }
        res = self._send_request("GET", "/uapi/overseas-stock/v1/trading/inquire-balance", headers_ext, params=params)
        if res and res.get("rt_cd") == "0":
            balances = res.get("output1", [])
            currency = res.get("output2", [])
            self.balance_updated.emit(balances, currency, res)
            return balances, currency
        self.api_error.emit("잔고 조회 실패")
        self.balance_updated.emit([], [], res)
        return [], []
