# taitan/data/news.py

from datetime import datetime
from typing import List
import uuid

# class NewsCollector:
#     """
#     뉴스 수집기 (더미)
#     - 나중에 실제 뉴스 API / 크롤러로 교체
#     """

#     def __init__(self, logger):
#         self.logger = logger
#         self.logger.info("NewsCollector initialized")

#     def fetch_latest(self) -> List[dict]:
#         """
#         최신 뉴스 목록 반환 (더미)
#         """
#         now = datetime.utcnow()

#         dummy_news = [
#             {
#                 "title": "Dummy news headline",
#                 "source": "MockSource",
#                 "published_at": now.isoformat(),
#                 "tickers": ["AAPL", "TSLA"],
#             }
#         ]

#         self.logger.info(
#             "Fetched %s news items",
#             len(dummy_news),
#         )

#         return dummy_news
    
#     def fetch_top3(self):
#         return [
#             {
#                 "id": "n1",
#                 "title": "Dummy news 1",
#                 "tickers": ["AAPL"],
#                 "published_at": "...",
#             },
#             {
#                 "id": "n2",
#                 "title": "Dummy news 2",
#                 "tickers": ["TSLA"],
#                 "published_at": "...",
#             },
#             {
#                 "id": "n3",
#                 "title": "Dummy news 3",
#                 "tickers": ["NVDA"],
#                 "published_at": "...",
#             },
#         ]

# 뉴스 강제 생성 TEST 위 코드가 기존 코드
class NewsCollector:
    def __init__(self, logger):
        self.logger = logger
        self._counter = 0

    def fetch_top3(self):
        now = datetime.utcnow().isoformat()

        uid = uuid.uuid4().hex

        return [
            {
                "id": f"force_{uid}_1",
                "tickers": ["AAPL"],
                "title": "Forced breaking news",
                "published_at": now,
            },
            {
                "id": f"force_{uid}_2",
                "tickers": ["MSFT"],
                "title": "Forced secondary news",
                "published_at": now,
            },
            {
                "id": f"force_{uid}_3",
                "tickers": ["NVDA"],
                "title": "Forced tertiary news",
                "published_at": now,
            },
        ]