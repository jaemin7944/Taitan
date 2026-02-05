import requests
from bs4 import BeautifulSoup
from typing import List, Dict


class NewsCollector:
    URL = "https://www.stocktitan.net/news/trending.html"

    def __init__(self, logger):
        self.logger = logger
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0"
        })

    def fetch_top3(self) -> List[Dict]:
        """
        StockTitan trending 뉴스 상위 3개 수집
        """
        try:
            res = self.session.get(self.URL, timeout=10)
            res.raise_for_status()
        except Exception as e:
            self.logger.error("Failed to fetch StockTitan news: %s", e)
            return []

        soup = BeautifulSoup(res.text, "html.parser")
        cards = soup.select("div.news-card")

        news_list = []

        for idx, card in enumerate(cards[:3]):
            # ----------------------------
            # 티커
            # ----------------------------
            symbol_el = card.select_one("a.news-card-symbol.symbol-link")
            if not symbol_el:
                continue

            ticker = symbol_el.get_text(strip=True)

            # ----------------------------
            # 제목
            # ----------------------------
            title_el = card.select_one("a.news-card-title")
            if not title_el:
                continue

            title = title_el.get_text(strip=True)

            # ----------------------------
            # 뉴스 ID (페이지 내 유니크)
            # ----------------------------
            link = title_el.get("href", "")
            news_id = link or f"stocktitan_{idx}_{ticker}"

            news_list.append({
                "id": news_id,
                "title": title,
                "tickers": [ticker],
            })

        self.logger.info(
            "Fetched %d StockTitan news items",
            len(news_list),
        )

        for n in news_list:
            self.logger.info(
                "News: id=%s ticker=%s title=%s",
                n["id"], n["tickers"][0], n["title"]
            )

        return news_list
