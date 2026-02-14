# taitan/broker/kis_broker.py

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any
import uuid


@dataclass
class OrderResult:
    ok: bool
    raw: Dict[str, Any]
    msg: str = ""


class KisBroker:
    """
    지정가 주문 전용 Broker
    - Engine은 buy_limit / sell_limit 만 호출
    - 시장가 주문은 지원하지 않음
    """

    def __init__(self, kis_client, logger, config: dict):
        self.kis = kis_client
        self.logger = logger

        self.cano = config["kis"]["cano"]
        self.acnt_prdt_cd = config["kis"]["acnt_prdt_cd"]

        self.dry_run = bool(config.get("trade", {}).get("dry_run", True))
        self.ovrs_excg_cd = config.get("trade", {}).get("ovrs_excg_cd", "NASD")
        self.order_div = config.get("trade", {}).get("order_div", "00")  # 00: 지정가

    # =====================================================
    # 1️⃣ 지정가 매수
    # =====================================================
    def buy_limit(self, ticker: str, qty: int, price: float) -> OrderResult:
        return self._order(
            side="BUY",
            ticker=ticker,
            qty=qty,
            price=price,
        )

    # =====================================================
    # 2️⃣ 지정가 매도
    # =====================================================
    def sell_limit(self, ticker: str, qty: int, price: float) -> OrderResult:
        return self._order(
            side="SELL",
            ticker=ticker,
            qty=qty,
            price=price,
        )

    # =====================================================
    # 내부 주문 처리
    # =====================================================
    def _order(self, side: str, ticker: str, qty: int, price: float) -> OrderResult:

        body = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "OVRS_EXCG_CD": self.ovrs_excg_cd,
            "PDNO": ticker.upper(),
            "ORD_QTY": str(qty),
            "ORD_UNPR": str(round(price, 2)),
            "SLL_BUY_DVSN_CD": "02" if side == "SELL" else "01",
            "ORD_DVSN_CD": self.order_div,  # 지정가
        }

        path = "/uapi/overseas-stock/v1/trading/order"
        tr_id = "TTTC0802U" if side == "BUY" else "TTTC0801U"

        if self.dry_run:
            self.logger.warning("[DRY-RUN][%s] %s", side, body)
            return OrderResult(
                ok=True,
                raw={"dry_run": True, "body": body},
                msg="dry_run",
            )

        headers_extra = {
            "gt_uid": str(uuid.uuid4()),
        }

        res = self.kis.post(
            path=path,
            tr_id=tr_id,
            json_body=body,
            headers_extra=headers_extra,
        )

        ok = (res.get("rt_cd") == "0")
        msg = res.get("msg1", "")

        if ok:
            self.logger.info(
                "[ORDER][%s] ACCEPTED: %s %s @ %s",
                side,
                ticker,
                qty,
                price,
            )
        else:
            self.logger.error("[ORDER][%s] FAILED: %s", side, res)

        return OrderResult(ok=ok, raw=res, msg=msg)
