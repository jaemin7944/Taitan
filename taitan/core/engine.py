# taitan/core/engine.py

from datetime import datetime
from taitan.data.news import NewsCollector
from taitan.core.strategies.simple_news_strategy import SimpleNewsStrategy

class Engine:
    """
    타이탄 엔진
    - 판단 로직의 중심
    - 스케줄러가 주기적으로 호출
    """

    def __init__(self, config: dict, logger):
        self.config = config
        self.logger = logger

        # 내부 상태 (나중에 포지션/잔고/캐시 등으로 확장)
        self._tick_count = 0
        self._last_run_time = None

        self.news_collector = NewsCollector(logger)
        # 전략 로딩 (지금은 하나)
        self.strategy = SimpleNewsStrategy(config, logger)

        self.logger.info("Engine initialized")

    def run_once(self):
        """
        스케줄러가 호출하는 단일 진입점
        """
        self._tick_count += 1
        now = datetime.utcnow()
    
        self.logger.info(
            "Engine tick #%s (utc=%s)",
            self._tick_count,
            now.isoformat(),
        )
    
        # 1. 데이터 수집
        news_list = self.news_collector.fetch_latest()
    
        # 2. 전략 판단 (딱 한 번!)
        decision = self.strategy.evaluate(news_list)
    
        # 3. 판단 결과 처리
        if decision:
            self.logger.info(
                "Decision: action=%s ticker=%s score=%s reason=%s",
                decision.action,
                decision.ticker,
                decision.score,
                decision.reason,
            )
    
        # 4. 상태 갱신
        self._last_run_time = now
    