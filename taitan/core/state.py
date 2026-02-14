# taitan/core/state.py

import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Set


class State:
    """
    Titan 상태 관리
    position:
        NONE
        ORDER_PENDING
        HOLDING
    """

    def __init__(self, logger, state_file: Optional[Path] = None):
        self.logger = logger
        self.state_file = state_file

        # =========================
        # 포지션 관련
        # =========================
        self.position: str = "NONE"
        self.pending_order_id: Optional[str] = None
        self.pending_since: Optional[datetime] = None

        self.ticker: Optional[str] = None
        self.entry_price: Optional[float] = None

        # 주문 대기 상태
        self.order_id: Optional[str] = None
        self.pending_side: Optional[str] = None  # BUY / SELL

        # =========================
        # 뉴스 관련
        # =========================
        self.news_reference_price: Optional[float] = None
        self.news_reference_time: Optional[datetime] = None
        self.last_top3_news_ids: List[str] = []

        # =========================
        # 기타
        # =========================
        self.traded_tickers: Set[str] = set()

        if self.state_file and self.state_file.exists():
            self.load()

        self.logger.info("State initialized")

    # ==================================================
    # 주문 대기 진입
    # ==================================================
    def enter_pending(self, ticker: str, entry_price: float, order_id: Optional[str], side: str):
        self.position = "ORDER_PENDING"
        self.ticker = ticker
        self.entry_price = entry_price
        self.order_id = order_id
        self.pending_side = side
        self.save()

        self.logger.info(
            "ENTER ORDER_PENDING: %s price=%.4f order_id=%s",
            ticker,
            entry_price,
            order_id,
        )

    # ==================================================
    # 체결 완료
    # ==================================================
    def confirm_filled(self):
        if self.position != "ORDER_PENDING":
            return

        self.position = "HOLDING"
        self.order_id = None
        self.pending_side = None
        self.save()

        self.logger.info("ORDER FILLED → HOLDING")

    # ==================================================
    # 주문 취소
    # ==================================================
    def cancel_pending(self):
        self.logger.info("CANCEL PENDING ORDER: %s", self.order_id)

        self.position = "NONE"
        self.ticker = None
        self.entry_price = None
        self.order_id = None
        self.pending_side = None
        self.save()

    # ==================================================
    # HOLDING 종료
    # ==================================================
    def exit_position(self):
        self.logger.info("EXIT POSITION: %s", self.ticker)

        self.position = "NONE"
        self.ticker = None
        self.entry_price = None
        self.order_id = None
        self.pending_side = None
        self.news_reference_price = None
        self.news_reference_time = None

        self.save()

    # ==================================================
    # 뉴스
    # ==================================================
    def set_news_reference(self, price: float, time: datetime):
        self.news_reference_price = price
        self.news_reference_time = time
        self.save()

    def clear_news_reference(self):
        self.news_reference_price = None
        self.news_reference_time = None
        self.save()

    def is_new_top3(self, current_top3_ids: List[str]) -> bool:
        return current_top3_ids != self.last_top3_news_ids

    # ==================================================
    # 저장 / 로드
    # ==================================================
    def save(self):
        if not self.state_file:
            return

        data = {
            "position": self.position,
            "ticker": self.ticker,
            "entry_price": self.entry_price,
            "order_id": self.order_id,
            "pending_side": self.pending_side,
            "news_reference_price": self.news_reference_price,
            "news_reference_time": self.news_reference_time.isoformat()
            if self.news_reference_time else None,
            "last_top3_news_ids": self.last_top3_news_ids,
            "traded_tickers": list(self.traded_tickers),
            "pending_order_id": self.pending_order_id,
            "pending_since": self.pending_since.isoformat() if self.pending_since else None,

        }

        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load(self):
        with open(self.state_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.position = data.get("position", "NONE")
        self.ticker = data.get("ticker")
        self.entry_price = data.get("entry_price")
        self.order_id = data.get("order_id")
        self.pending_side = data.get("pending_side")

        self.news_reference_price = data.get("news_reference_price")

        nrt = data.get("news_reference_time")
        self.news_reference_time = datetime.fromisoformat(nrt) if nrt else None

        self.last_top3_news_ids = data.get("last_top3_news_ids", [])
        self.traded_tickers = set(data.get("traded_tickers", []))

        self.logger.info("State loaded from file")

        self.pending_order_id = data.get("pending_order_id")
        ps = data.get("pending_since")
        self.pending_since = datetime.fromisoformat(ps) if ps else None

    def set_order_pending(self, order_id: str):
        self.position = "ORDER_PENDING"
        self.pending_order_id = order_id
        self.pending_since = datetime.utcnow()
        self.save()
        self.logger.info("ORDER_PENDING set: %s", order_id)
    
    
    def clear_pending(self):
        self.pending_order_id = None
        self.pending_since = None
        self.save()
    