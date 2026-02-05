from datetime import datetime, time

def is_us_regular_market_open(now_utc: datetime) -> bool:
    """
    미국 정규장 여부 (UTC 기준)
    14:30 ~ 21:00 UTC
    """
    market_open = time(14, 30)
    market_close = time(21, 0)

    now_time = now_utc.time()
    return market_open <= now_time <= market_close
