# taitan/core/state.py

import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Set, List
from taitan.core.decision import Decision


class State:
    """
    시스템 상태 관리
    - 포지션
    - 뉴스 기준 정보
    - 재매수 금지
    - 사용자 설정 값
    """

    def __init__(self, logger, state_file: Optional[Path] = None):
        self.logger = logger
        self.state_file = state_file

        # -------------------------
        # 포지션 상태
        # -------------------------
        self.position: str = "NONE"     # NONE / LONG
        self.ticker: Optional[str] = None
        self.entry_price: Optional[float] = None

        # -------------------------
        # 뉴스 기준 정보
        # -------------------------
        self.news_reference_price: Optional[float] = None
        self.news_reference_time: Optional[datetime] = None
        self.last_top3_news_ids: List[str] = []

        # -------------------------
        # 전략 제어 값 (UI 연동 대상)
        # -------------------------
        self.price_change_threshold: float = 3.0  # %

        # -------------------------
        # 재매수 금지
        # -------------------------
        self.traded_tickers: Set[str] = set()

        # -------------------------
        # 기타
        # -------------------------
        self.last_decision: Optional[Decision] = None
        self.last_updated: Optional[datetime] = None

        # 상태 파일 로드
        if self.state_file and self.state_file.exists():
            self.load()

        self.logger.info("State initialized")

    # ==================================================
    # 상태 반영
    # ==================================================
    def apply_decision(self, decision: Decision):
        self.last_decision = decision
        self.last_updated = datetime.utcnow()

        if decision.action == "BUY":
            self.position = "LONG"
            self.ticker = decision.ticker
            self.entry_price = decision.score  # 임시 (나중에 실제 체결가)

            self.traded_tickers.add(decision.ticker)

        elif decision.action == "SELL":
            self.position = "NONE"
            self.ticker = None
            self.entry_price = None
            self.news_reference_price = None
            self.news_reference_time = None

        self.save()

        self.logger.info(
            "State updated: position=%s ticker=%s",
            self.position,
            self.ticker,
        )

    # ==================================================
    # 뉴스 관련
    # ==================================================
    def update_news_reference(
        self,
        price: float,
        news_time: datetime,
        top3_ids: List[str],
    ):
        self.news_reference_price = price
        self.news_reference_time = news_time
        self.last_top3_news_ids = top3_ids
        self.save()

        self.logger.info(
            "News reference updated: price=%s time=%s",
            price,
            news_time.isoformat(),
        )

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
            "news_reference_price": self.news_reference_price,
            "news_reference_time": self.news_reference_time.isoformat()
            if self.news_reference_time else None,
            "last_top3_news_ids": self.last_top3_news_ids,
            "price_change_threshold": self.price_change_threshold,
            "traded_tickers": list(self.traded_tickers),
        }

        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load(self):
        with open(self.state_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.position = data.get("position", "NONE")
        self.ticker = data.get("ticker")
        self.entry_price = data.get("entry_price")

        self.news_reference_price = data.get("news_reference_price")
        nrt = data.get("news_reference_time")
        self.news_reference_time = datetime.fromisoformat(nrt) if nrt else None

        self.last_top3_news_ids = data.get("last_top3_news_ids", [])
        self.price_change_threshold = data.get("price_change_threshold", 3.0)
        self.traded_tickers = set(data.get("traded_tickers", []))

        self.logger.info("State loaded from file")
