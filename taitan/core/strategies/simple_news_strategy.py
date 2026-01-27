from typing import Optional
from .base import BaseStrategy
from taitan.core.decision import Decision


class SimpleNewsStrategy(BaseStrategy):
    def evaluate(self, news_list) -> Optional[Decision]:
        self.logger.info(
            "SimpleNewsStrategy evaluating %s news items",
            len(news_list),
        )

        if not news_list:
            return Decision(action="HOLD", ticker=None, reason="no news", score=0.0)

        # 더미: 첫 뉴스의 첫 ticker를 고름
        first = news_list[0]
        tickers = first.get("tickers", [])
        title = first.get("title", "")

        if not tickers:
            return Decision(action="HOLD", ticker=None, reason="no tickers in news", score=0.0)

        # 아직 매매는 안 하니까 HOLD로 반환만 해두자
        return Decision(
            action="HOLD",
            ticker=tickers[0],
            reason=f"news received: {title}",
            score=1.0,
        )
