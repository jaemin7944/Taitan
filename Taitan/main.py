from __future__ import annotations

import sys
from PySide6.QtWidgets import QApplication

from venv.config import load_settings
from titantrade.state import BotState
from titantrade.services.stocktitan_scraper import StockTitanScraper
from titantrade.services.marketdata_yf import MarketDataYF
from titantrade.services.decision_engine import DecisionEngine
from titantrade.services.kis_api import KISAPI
from titantrade.services.runner import RunnerConfig, TitanRunner
from titantrade.ui.main_window import MainWindow


def main() -> int:
    s = load_settings()

    scraper = StockTitanScraper(base_url=s.stocktitan_trending_url, user_agent=s.user_agent)
    market = MarketDataYF()
    engine = DecisionEngine(buy_threshold_pct=s.buy_threshold_pct)
    kis = KISAPI(
        base_url=s.kis_api_base_url,
        app_key=s.kis_app_key,
        app_secret=s.kis_app_secret,
        cano=s.cano,
        acnt_prdt_cd=s.acnt_prdt_cd,
    )

    cfg = RunnerConfig(
        poll_interval_sec=s.poll_interval_sec,
        top_n_news=5,
        max_buy_per_ticker=s.max_buy_per_ticker,
        ovrs_excg_cd=s.ovrs_excg_cd,
    )

    app = QApplication(sys.argv)

    runner = TitanRunner(
        cfg=cfg,
        scraper=scraper,
        market=market,
        engine=engine,
        kis=kis,
        state=BotState(),
        on_log=lambda m: None,  # UI에서 교체
    )

    win = MainWindow(runner=runner)

    # UI 로그 연결
    runner.on_log = win.append_log

    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
