# taitan/core/engine.py

from datetime import datetime, timezone
from taitan.data.news import NewsCollector
from taitan.core.strategies.gpt_news_strategy import GPTNewsStrategy
from taitan.core.state import State
from taitan.data.market import Market
from taitan.infra.kis_client import KisClient
from pathlib import Path
from taitan.broker.kis_broker import KisBroker
from taitan.utils.time import is_us_regular_market_open
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
        self.strategy = GPTNewsStrategy(config, logger)

        self.logger.info("Engine initialized")

    def run_once(self):
        self._tick_count += 1
        now = datetime.now(timezone.utc)

        self.logger.info(
            "Engine tick #%s (utc=%s)",
            self._tick_count,
            now.isoformat(),
        )

        # =================================================
        # 0. HOLDING 상태 → TP / SL 체크 (최우선)
        # =================================================
        if self.state.position == "HOLDING":
            ticker = self.state.ticker
            entry_price = self.state.entry_price

            price = self.market.get_current_price(ticker)
            if price is None:
                self.logger.info("Price unavailable, skip TP/SL check")
                return

            tp_pct = self.config["trade"]["take_profit_pct"]
            sl_pct = self.config["trade"]["stop_loss_pct"]

            tp_price = entry_price * (1 + tp_pct / 100)
            sl_price = entry_price * (1 - sl_pct / 100)

            self.logger.info(
                "HOLDING check: %s current=%.2f TP=%.2f SL=%.2f",
                ticker, price, tp_price, sl_price,
            )

            if price >= tp_price:
                self._exit_position("TAKE_PROFIT", price)
                return

            if price <= sl_price:
                self._exit_position("STOP_LOSS", price)
                return

            return

        # =================================================
        # 1. 뉴스 Top3 수집
        # =================================================
        top3_news = self.news_collector.fetch_top3()
        top3_ids = [n["id"] for n in top3_news]

        if not self.state.is_new_top3(top3_ids):
            self.logger.info("No new top3 news detected")
            return

        self.logger.info("New top3 news detected")

        self.state.last_top3_news_ids = top3_ids
        self.state.save()

        # =================================================
        # 2. 뉴스 기준가 설정 (한 번만)
        # =================================================
        if self.state.news_reference_price is None:
            ref_ticker = self.strategy.peek_ticker(top3_news)
            if ref_ticker:
                ref_price = self.market.get_current_price(ref_ticker)
                if ref_price is not None:
                    self.state.set_news_reference(ref_price, now)
                    self.logger.info(
                        "News reference price set: %s %.2f",
                        ref_ticker, ref_price,
                    )

        # =================================================
        # 3. 전략 판단
        # =================================================
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

        # =================================================
        # 4. BUY 처리 (정규장 + 돌파 조건)
        # =================================================
        if decision.action == "BUY" and self.state.position == "NONE":

            if not is_us_regular_market_open(now):
                self.logger.info("Market closed (US regular hours only), skip BUY")
                return

            price = self.market.get_current_price(decision.ticker)
            if price is None:
                self.logger.info("Price unavailable, skip BUY")
                return

            ref_price = self.state.news_reference_price
            breakout_pct = self.config["trade"]["buy_breakout_pct"]
            breakout_price = ref_price * (1 + breakout_pct / 100)

            self.logger.info(
                "BUY breakout check: current=%.2f ref=%.2f target=%.2f",
                price, ref_price, breakout_price,
            )

            if price < breakout_price:
                self.logger.info("Breakout not reached, skip BUY")
                return

            qty = 1
            result = self.broker.buy(decision.ticker, qty=qty, price=price)

            if not result.ok:
                self.logger.error(
                    "BUY failed: ticker=%s msg=%s",
                    decision.ticker, result.msg,
                )
                return

            self.logger.info(
                "BUY success: %s qty=%s price=%.2f",
                decision.ticker, qty, price,
            )

            self.state.enter_position(
                ticker=decision.ticker,
                entry_price=price,
            )

            self.state.clear_news_reference()

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

    def _check_tp_sl(self):
        ticker = self.state.ticker
        entry_price = self.state.entry_price

        price = self.market.get_current_price(ticker)
        if price is None:
            self.logger.info("Price unavailable, skip TP/SL check")
            return

        tp_pct = self.config["trade"]["take_profit_pct"]
        sl_pct = self.config["trade"]["stop_loss_pct"]

        tp_price = entry_price * (1 + tp_pct / 100)
        sl_price = entry_price * (1 - sl_pct / 100)

        self.logger.info(
            "TP/SL check: price=%.2f TP=%.2f SL=%.2f",
            price, tp_price, sl_price
        )

        if price >= tp_price:
            self._sell("TAKE_PROFIT", price)
        elif price <= sl_price:
            self._sell("STOP_LOSS", price)

    def _sell(self, reason: str, price: float):
        ticker = self.state.ticker
    
        self.logger.info(
            "SELL triggered (%s): %s at %.2f",
            reason, ticker, price
        )
    
        if self.config["trade"]["dry_run"]:
            self.logger.info("[DRY-RUN] SELL %s", ticker)
        else:
            self.broker.sell_market(ticker)
    
        # 상태 초기화
        self.state.clear_position()
