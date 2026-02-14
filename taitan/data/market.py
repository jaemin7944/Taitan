# taitan/data/market.py

from typing import Optional, Dict


class Market:
    """
    조회 전용 레이어
    - 현재가 조회
    - 해외 보유 종목 조회
    """

    def __init__(self, kis_client, logger, cano: str, acnt_prdt_cd: str):
        self.kis = kis_client
        self.logger = logger
        self.cano = cano
        self.acnt_prdt_cd = acnt_prdt_cd

    # =====================================================
    # 1️⃣ 현재가 조회
    # =====================================================
    def get_current_price(self, ticker: str) -> Optional[float]:

        res = self.kis.get(
            path="/uapi/overseas-price/v1/quotations/price",
            tr_id="HHDFS00000300",
            params={
                "AUTH": "",
                "EXCD": "NAS",
                "SYMB": ticker.upper(),
            },
        )

        output = res.get("output")
        if not output:
            self.logger.error(f"[PRICE] output missing: {res}")
            return None

        last = output.get("last")
        p_last = output.get("p_last")
        base = output.get("base")

        def valid(v):
            try:
                v = float(v)
                return v if v > 0 else None
            except:
                return None

        return valid(last) or valid(p_last) or valid(base)

    # =====================================================
    # 2️⃣ 보유 종목 조회
    # =====================================================
    def get_positions(self) -> Dict[str, Dict]:

        res = self.kis.get(
            path="/uapi/overseas-stock/v1/trading/inquire-balance",
            tr_id="TTTS3012R",
            params={
                "CANO": self.cano,
                "ACNT_PRDT_CD": self.acnt_prdt_cd,
                "OVRS_EXCG_CD": "NASD",
                "TR_CRCY_CD": "USD",
                "CTX_AREA_FK200": "",
                "CTX_AREA_NK200": "",
            },
        )

        output = res.get("output1", [])
        positions = {}

        for item in output:
            ticker = item.get("ovrs_pdno")
            qty = int(item.get("ovrs_cblc_qty", 0))
            avg_price = float(item.get("pchs_avg_pric", 0))

            if ticker and qty > 0:
                positions[ticker] = {
                    "qty": qty,
                    "avg_price": avg_price,
                }

        return positions

    # =====================================================
    # 3️⃣ 보유 여부
    # =====================================================
    def is_holding(self, ticker: str) -> bool:
        positions = self.get_positions()
        return ticker.upper() in positions
    
    def check_order_filled(self, order_id: str) -> bool:
        """
        주문 체결 여부 확인
        체결되었으면 True, 아니면 False
        """
        try:
            res = self.kis.get(
                path="/uapi/overseas-stock/v1/trading/inquire-ccnl",
                tr_id="TTTS3035R",
                params={
                    "CANO": self.cano,
                    "ACNT_PRDT_CD": self.acnt_prdt_cd,
                    "ODNO": order_id,
                    "CTX_AREA_FK200": "",
                    "CTX_AREA_NK200": ""
                }
            )

            if res.get("rt_cd") != "0":
                self.logger.error("Order check failed: %s", res)
                return False

            output = res.get("output1", [])
            if not output:
                return False

            # 체결수량 확인
            filled_qty = sum(int(item.get("cncl_qty", 0)) for item in output)

            return filled_qty > 0

        except Exception as e:
            self.logger.error("Order check exception: %s", e)
            return False

