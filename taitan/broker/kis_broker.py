# taitan/broker/kis_broker.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict, Any
import uuid

@dataclass
class OrderResult:
    ok: bool
    raw: Dict[str, Any]
    msg: str = ""

class KisBroker:
    """
    - KIS 해외주식 주문 실행 담당
    - Engine은 여기로 buy/sell만 호출
    """

    def __init__(self, kis_client, logger, config: dict):
        self.kis = kis_client
        self.logger = logger
        self.cano = config["kis"]["cano"]
        self.acnt_prdt_cd = config["kis"]["acnt_prdt_cd"]
        self.dry_run = bool(config.get("trade", {}).get("dry_run", True))
        self.ovrs_excg_cd = config.get("trade", {}).get("ovrs_excg_cd", "NAS")
        self.order_div = config.get("trade", {}).get("order_div", "00")

    def buy(self, ticker: str, qty: int, price: float) -> OrderResult:
        return self._order(side="BUY", ticker=ticker, qty=qty, price=price)

    def sell(self, ticker: str, qty: int, price: float) -> OrderResult:
        return self._order(side="SELL", ticker=ticker, qty=qty, price=price)

    def _order(self, side: str, ticker: str, qty: int, price: float) -> OrderResult:
        body = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "OVRS_EXCG_CD": self.ovrs_excg_cd,
            "PDNO": ticker,
            "ORD_QTY": str(qty),
            "ORD_UNPR": str(price),
            "SLL_BUY_DVSN_CD": "02" if side == "SELL" else "01",
            "ORD_DVSN_CD": self.order_div,
        }

        # 해외주식 주문 엔드포인트 (너가 이미 쓰던 경로)
        path = "/uapi/overseas-stock/v1/trading/order"

        # TR_ID는 너가 이미 쓰던 값 사용(실계: TTTC0802U/TTTC0801U 등)
        tr_id = "TTTC0802U" if side == "BUY" else "TTTC0801U"

        if self.dry_run:
            self.logger.warning("[DRY-RUN] %s order skipped: %s", side, body)
            return OrderResult(ok=True, raw={"dry_run": True, "body": body}, msg="dry_run")

        headers_extra = {
            "gt_uid": str(uuid.uuid4()),
        }

        # 주문은 해시키(hashkey) 넣으면 더 안전한데, KIS 문서/예제에선 선택사항으로도 다룸 :contentReference[oaicite:2]{index=2}
        # 우리 KisClient가 hashkey를 지원하면 여기서 넣고, 아니면 일단 없이도 진행 가능.
        res = self.kis.post(path=path, tr_id=tr_id, json_body=body, headers_extra=headers_extra)

        ok = (res.get("rt_cd") == "0")
        msg = res.get("msg1", "")
        if ok:
            self.logger.info("[ORDER][%s] accepted: %s %s@%s", side, ticker, qty, price)
        else:
            self.logger.error("[ORDER][%s] failed: %s", side, res)

        return OrderResult(ok=ok, raw=res, msg=msg)
