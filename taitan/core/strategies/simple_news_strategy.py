from typing import Optional
from taitan.core.decision import Decision
from .base import BaseStrategy

class SimpleNewsStrategy(BaseStrategy):
    def __init__(self, market, state, logger, config):
        super().__init__(config, logger)   # 🔥 핵심 수정

        self.market = market
        self.state = state
        
        # yaml에서 buy threshold 읽기
        self.buy_threshold = config.get("trading", {}).get("buy_threshold_pct", 1.0)

    def evaluate(self, news_list) -> Optional[Decision]:
        self.logger.info(
            "SimpleNewsStrategy evaluating %s news items",
            len(news_list),
        )

        if not news_list:
            return Decision(action="HOLD", ticker=None, reason="no news", score=0.0)

        first = news_list[0]
        tickers = first.get("tickers", [])
        title = first.get("title", "")

        if not tickers:
            return Decision(action="HOLD", ticker=None, reason="no tickers in news", score=0.0)

        ticker = tickers[0]

        # -----------------------------
        # 🔑 score 계산 (지금은 더미)
        # -----------------------------
        score = 1.0

        # -----------------------------
        # 🔑 BUY 조건
        # -----------------------------
        if score >= self.buy_threshold and self.state.position == "NONE":
            return Decision(
                action="BUY",
                ticker=ticker,
                score=score,
                reason=f"score {score} >= threshold {self.buy_threshold}",
            )

        return Decision(
            action="HOLD",
            ticker=ticker,
            score=score,
            reason=f"score {score} < threshold or already holding",
        )
