# taitan/core/engine.py

from datetime import datetime
from taitan.data.news import NewsCollector
from taitan.core.strategies.simple_news_strategy import SimpleNewsStrategy
from taitan.core.state import State
from taitan.data.market import Market
from taitan.infra.kis_client import KisClient
from pathlib import Path
from taitan.broker.kis_broker import KisBroker
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
        # State 
        # -------------------------
        state_file = Path("state.json")
        self.state = State(logger, state_file=state_file)

        self.kis = KisClient(
            app_key=config["kis"]["app_key"],
            app_secret=config["kis"]["app_secret"],
            # access_token=config["kis"]["access_token"],
            base_url=config["kis"]["base_url"],
        )

        self.market = Market(self.kis, logger)

        self.broker = KisBroker(self.kis, self.logger, config)

        # -------------------------
        # 전략
        # -------------------------
        self.strategy = SimpleNewsStrategy(
            market=self.market,
            state=self.state,
            logger=self.logger,
            config=self.config,
        )

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
        # 0. HOLDING 상태: 익절/손절 체크
        # ---------------------------------
        if self.state.position == "HOLDING":
            ticker = self.state.ticker

            price = self.market.get_current_price(ticker)
            if price is None:
                self.logger.info("Price unavailable, skip TP/SL check")
                return

            tp = self.state.data["take_profit_price"]
            sl = self.state.data["stop_loss_price"]

            self.logger.info(
                "HOLDING check: %s current=%.2f TP=%.2f SL=%.2f",
                ticker, price, tp, sl
            )

            if price >= tp:
                self._exit_position(
                    action="TAKE_PROFIT",
                    price=price,
                )
                return

            if price <= sl:
                self._exit_position(
                    action="STOP_LOSS",
                    price=price,
                )
                return

            # 아직 조건 미충족 → 다음 tick 대기
            return


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
        # 4. 전략 판단
        # ---------------------------------
        decision = self.strategy.evaluate(top3_news)

        if not decision:
            return
        
        self.logger.info(
            "Decision: action=%s ticker=%s score=%s reason=%s",
            decision.action,
            decision.ticker,
            decision.score,
            decision.reason,
        )

        # ---------------------------------
        # 5. Buy 판단 처리 (가격 연동)
        # ---------------------------------

        if decision.action == "BUY" and self.state.position == "NONE":
            price = self.market.get_current_price(decision.ticker)
            if price is None:
                self.logger.info("Price unavailable, skip BUY")
                return      

            qty = 1  # 일단 1주 (나중에 UI/설정으로)
            result = self.broker.buy(decision.ticker, qty=qty, price=price)     

            if not result.ok:
                self.logger.error("BUY failed, keep position NONE. msg=%s", result.msg)
                return      

            # 주문 성공(또는 dry-run 성공)이면 상태 진입
            self.state.enter_position(ticker=decision.ticker, entry_price=price)


        self._last_run_time = now

    def _exit_position(self, action: str, price: float):
        ticker = self.state.data["ticker"]
        entry = self.state.data["entry_price"]

        pnl = (price - entry) / entry * 100

        self.logger.info(
            "%s: %s exit_price=%.2f PnL=%.2f%%",
            action,
            ticker,
            price,
            pnl,
        )

        qty = 1  # TODO: 나중에 state에 보유 수량 저장
        result = self.broker.sell(ticker=ticker, qty=qty, price=price)

        if not result.ok:
            self.logger.error(
                "SELL failed, keep HOLDING. action=%s msg=%s",
                action,
                result.msg,
            )
            return

        # 매도 성공(또는 dry-run 성공) 시에만 상태 종료
        self.state.exit_position()
