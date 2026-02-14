# taitan/core/engine.py

from datetime import datetime, timezone
from pathlib import Path

from taitan.data.news import NewsCollector
from taitan.core.strategies.gpt_news_strategy import GPTNewsStrategy
from taitan.core.state import State
from taitan.data.market import Market
from taitan.infra.kis_client import KisClient
from taitan.broker.kis_broker import KisBroker
from taitan.utils.time import is_us_regular_market_open
from taitan.core.gpt_cache import GPTCache


class Engine:

    def __init__(self, config: dict, logger):
        self.config = config
        self.logger = logger

        self._tick_count = 0

        self.news_collector = NewsCollector(logger)

        state_file = Path("state.json")
        self.state = State(logger, state_file=state_file)

        self.kis = KisClient(
            app_key=config["kis"]["app_key"],
            app_secret=config["kis"]["app_secret"],
            base_url=config["kis"]["base_url"],
        )

        self.market = Market(
            self.kis,
            logger,
            cano=config["kis"]["cano"],
            acnt_prdt_cd=config["kis"]["acnt_prdt_cd"],
        )

        self.broker = KisBroker(self.kis, self.logger, config)

        self.strategy = GPTNewsStrategy(config, logger)

        cache_file = Path("gpt_cache.json")
        self.gpt_cache = GPTCache(cache_file, logger)

        self.logger.info("Engine initialized")

        # ==========================================
        # 🔄 계좌와 state 동기화
        # ==========================================
        try:
            positions = self.market.get_positions()

            if positions:
                # 단일 포지션 전략 → 첫 번째 종목만 사용
                ticker = list(positions.keys())[0]
                avg_price = positions[ticker]["avg_price"]

                self.logger.warning(
                    "Account has open position → syncing state: %s @ %.4f",
                    ticker,
                    avg_price,
                )

                self.state.position = "HOLDING"
                self.state.ticker = ticker
                self.state.entry_price = avg_price
                self.state.save()

        except Exception as e:
            self.logger.error("Account sync failed: %s", e)


    def run_once(self):
        self._tick_count += 1
        now = datetime.now(timezone.utc)

        self.logger.info(
            "Engine tick #%s (utc=%s)",
            self._tick_count,
            now.isoformat(),
        )

        # =================================================
        # ORDER_PENDING → timeout 체크
        # =================================================
        if self.state.position == "ORDER_PENDING":
        
            order_id = self.state.pending_order_id

            # 드라이런이면 바로 체결 처리
            if self.config["trade"]["dry_run"]:
                self.logger.info("[DRY-RUN] Auto-fill pending order")
                self.state.position = "HOLDING"
                self.state.clear_pending()
                self.state.save()
                return

            # 실제 체결 확인
            filled = self.market.check_order_filled(order_id)

            if filled:
                self.logger.info("Order filled → switching to HOLDING")
                self.state.position = "HOLDING"
                self.state.clear_pending()
                self.state.save()
                return

            # 체결 안 됐으면 timeout 체크
            if self.state.pending_since:
                elapsed = (now - self.state.pending_since).total_seconds()
                timeout_sec = 30

                self.logger.info(
                    "ORDER_PENDING waiting: %.1fs / %ss",
                    elapsed, timeout_sec
                )

                if elapsed >= timeout_sec:
                    self.logger.warning("Order timeout → cancel & revert to NONE")
                    self.state.position = "NONE"
                    self.state.clear_pending()
                    self.state.save()

            return


        # =================================================
        # 0) HOLDING → TP/SL 체크
        # =================================================
        if self.state.position == "HOLDING":
            ticker = self.state.ticker
            entry_price = self.state.entry_price

            price = self.market.get_current_price(ticker)
            if price is None:
                return

            tp_pct = float(self.config.get("trade", {}).get("take_profit_pct", 10))
            sl_pct = float(self.config.get("trade", {}).get("stop_loss_pct", 5))

            tp_price = entry_price * (1 + tp_pct / 100)
            sl_price = entry_price * (1 - sl_pct / 100)

            self.logger.info(
                "HOLDING: %s current=%.4f TP=%.4f SL=%.4f",
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
        # 0-1) 실제 계좌 보유 여부 체크
        # =================================================
        try:
            positions = self.market.get_positions()
        except Exception as e:
            self.logger.error("Failed to fetch positions: %s", e)
            positions = {}

        if self.state.position == "NONE" and positions:
            self.logger.warning(
                "Real account has positions=%s → skip BUY",
                list(positions.keys()),
            )
            return

        # =================================================
        # 1) 뉴스 수집
        # =================================================
        top3_news = self.news_collector.fetch_top3()
        if not top3_news:
            return

        top3_ids = [n["id"] for n in top3_news]

        # if not self.state.is_new_top3(top3_ids):
        #     return

        self.state.last_top3_news_ids = top3_ids
        self.state.save()

        # =================================================
        # 2) 기준가 설정
        # =================================================
        if self.state.news_reference_price is None:
            ref_ticker = self.strategy.peek_ticker(top3_news)
            if ref_ticker:
                ref_price = self.market.get_current_price(ref_ticker)
                if ref_price:
                    self.state.set_news_reference(ref_price, now)

        # =================================================
        # 3) GPT 전략 판단
        # =================================================
        primary_news = top3_news[0]
        news_id = primary_news["id"]

        decision = self.gpt_cache.get(news_id)
        if not decision:
            decision = self.strategy.evaluate(top3_news)
            if decision:
                self.gpt_cache.set(news_id, decision)

        if not decision:
            return

        self.logger.info(
            "Decision: action=%s ticker=%s score=%s",
            decision.action,
            decision.ticker,
            decision.score,
        )
        # 🔥 테스트 강제 BUY
        decision.action = "BUY"
        decision.ticker = "AAPL"

        # =================================================
        # 4) BUY 처리 (지정가)
        # =================================================
        # if decision.action == "BUY" and self.state.position == "NONE":

        #     if not is_us_regular_market_open(now):
        #         return

        #     if self.market.is_holding(decision.ticker):
        #         return

        #     price = self.market.get_current_price(decision.ticker)
        #     if not price:
        #         return

        #     ref_price = self.state.news_reference_price
        #     if not ref_price:
        #         return

        #     breakout_pct = float(self.config.get("trade", {}).get("buy_breakout_pct", 0.5))
        #     breakout_price = ref_price * (1 + breakout_pct / 100)

        #     if price < breakout_price:
        #         return

        #     qty = int(self.config.get("trade", {}).get("qty", 1))

        #     slip_pct = float(self.config.get("trade", {}).get("buy_limit_slip_pct", 1.0))
        #     limit_price = round(price * (1 + slip_pct / 100), 2)

        #     result = self.broker.buy_limit(decision.ticker, qty=qty, price=limit_price)

        #     if not result.ok:
        #         self.logger.error("BUY failed: %s", result.msg)
        #         return

        #     order_id = result.raw.get("output", {}).get("ODNO", None)

        #     if not order_id:
        #         order_id = "DRYRUN"

        #     self.logger.info("Order submitted, switching to ORDER_PENDING: %s", order_id)

        #     self.state.set_order_pending(order_id)
        #     self.state.ticker = decision.ticker
        #     self.state.entry_price = limit_price
        #     self.state.save()

        #     self.state.clear_news_reference()\
        # 테스트용!!!
        if decision.action == "BUY" and self.state.position == "NONE":
        
            price = self.market.get_current_price(decision.ticker)
            if not price:
                return

            qty = 1
            limit_price = price  # 테스트용

            self.logger.info("TEST BUY(limit) %s @ %.2f", decision.ticker, limit_price)

            result = self.broker.buy_limit(decision.ticker, qty=qty, price=limit_price)

            if not result.ok:
                self.logger.error("BUY failed: %s", result.msg)
                return

            order_id = result.raw.get("output", {}).get("ODNO", "DRYRUN")

            self.state.set_order_pending(order_id)
            self.state.ticker = decision.ticker
            self.state.entry_price = limit_price
            self.state.save()

            return


    # =================================================
    # 지정가 매도
    # =================================================
    def _exit_position(self, reason: str, current_price: float):

        ticker = self.state.ticker
        entry = self.state.entry_price

        pnl = (current_price - entry) / entry * 100

        self.logger.info(
            "%s: %s current=%.4f entry=%.4f PnL=%.2f%%",
            reason, ticker, current_price, entry, pnl,
        )

        qty = int(self.config.get("trade", {}).get("qty", 1))

        slip_pct = float(self.config.get("trade", {}).get("sell_limit_slip_pct", 1.0))
        limit_price = round(current_price * (1 - slip_pct / 100), 2)

        result = self.broker.sell_limit(ticker=ticker, qty=qty, price=limit_price)

        if not result.ok:
            self.logger.error("SELL failed: %s", result.msg)
            return

        self.state.exit_position()
