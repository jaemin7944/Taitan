# taitan/core/engine.py

from datetime import datetime
from taitan.data.news import NewsCollector
from taitan.core.strategies.simple_news_strategy import SimpleNewsStrategy
from taitan.core.state import State
from taitan.data.market import Market
from taitan.infra.kis_client import KisClient
from pathlib import Path
class Engine:
    """
    타이탄 엔진
    - 판단 로직의 중심
    - 스케줄러가 주기적으로 호출
    """

    def __init__(self, config: dict, logger):
        self.config = config
        self.logger = logger

        # -------------------------
        # 엔진 내부 상태
        # -------------------------
        self._tick_count = 0
        self._last_run_time = None

        # -------------------------
        # 데이터 수집기
        # -------------------------
        self.news_collector = NewsCollector(logger)

        # -------------------------
        # 전략
        # -------------------------
        self.strategy = SimpleNewsStrategy(config, logger)

        # -------------------------
        # State 
        # -------------------------
        state_file = Path("state.json")
        self.state = State(logger, state_file=state_file)

        kis_client = KisClient(
            app_key=config["kis"]["app_key"],
            app_secret=config["kis"]["app_secret"],
            # access_token=config["kis"]["access_token"],
            base_url=config["kis"]["base_url"],
        )

        self.market = Market(kis_client, logger)


        self.logger.info("Engine initialized")

    def run_once(self):
        self._tick_count += 1
        now = datetime.utcnow()

        self.logger.info(
            "Engine tick #%s (utc=%s)",
            self._tick_count,
            now.isoformat(),
        )

        # ---------------------------------
        # 1. 뉴스 Top3 수집
        # ---------------------------------
        top3_news = self.news_collector.fetch_top3()
        top3_ids = [n["id"] for n in top3_news]

        # ---------------------------------
        # 2. 신규 Top3 감지
        # ---------------------------------
        if not self.state.is_new_top3(top3_ids):
            self.logger.info("No new top3 news detected")
            self._last_run_time = now
            return

        self.logger.info("New top3 news detected")

        # Top3 ID 갱신
        self.state.last_top3_news_ids = top3_ids
        self.state.save()

        # ---------------------------------
        # 3. 포지션 보유 중이면 여기서 종료
        # ---------------------------------
        if self.state.position != "NONE":
            self.logger.info("Position already open, skip trading logic")
            self._last_run_time = now
            return

        # ---------------------------------
        # 4. 다음 단계로 전달 (GPT / 가격 기준)
        # ---------------------------------
        decision = self.strategy.evaluate(top3_news)

        if decision:
            self.logger.info(
                "Decision: action=%s ticker=%s score=%s reason=%s",
                decision.action,
                decision.ticker,
                decision.score,
                decision.reason,
            )
            self.state.apply_decision(decision)

        self._last_run_time = now
