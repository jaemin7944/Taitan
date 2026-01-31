# test_market.py

from taitan.infra.config import load_config
from taitan.infra.logger import init_logger
from taitan.infra.kis_client import KisClient
from taitan.data.market import Market
from pathlib import Path

# ------------------------------------
# 1. config / logger 로드
# ------------------------------------
base_dir = Path(__file__).resolve().parent
config_dir = base_dir / "config"
log_dir = base_dir / "logs"

config = load_config(config_dir)
logger = init_logger(log_dir)

# ------------------------------------
# 2. KIS Client 생성
# ------------------------------------
kis_client = KisClient(
    app_key=config["kis"]["app_key"],
    app_secret=config["kis"]["app_secret"],
    base_url=config["kis"]["base_url"],
)

# ------------------------------------
# 3. Market 생성
# ------------------------------------
market = Market(kis_client, logger)

# ------------------------------------
# 4. 현재가 조회 테스트
# ------------------------------------
price = market.get_current_price("AAPL")
print("AAPL current price:", price)
