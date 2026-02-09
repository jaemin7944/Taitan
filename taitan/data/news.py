import cloudscraper
import xml.etree.ElementTree as ET
from typing import List, Dict
from bs4 import BeautifulSoup


class NewsCollector:
    RSS_URL = "https://www.stocktitan.net/rss"
    HOME_URL = "https://www.stocktitan.net/"
    TRENDING_URL = "https://www.stocktitan.net/news/trending.html"

    def __init__(self, logger):
        self.logger = logger

        self.scraper = cloudscraper.create_scraper(
            browser={
                "browser": "chrome",
                "platform": "windows",   # ⭐ mac → windows로 변경
                "mobile": False
            },
            delay=5   # ⭐ Cloudflare 회피 핵심
        )

        self.scraper.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        })


        # ⭐ 쿠키 확보
        try:
            self.scraper.get(self.HOME_URL, timeout=10)
            self.scraper.get(self.HOME_URL, timeout=10)
        except Exception:
            pass

    # -----------------------------
    def fetch_top3(self) -> List[Dict]:

        news = self._fetch_rss()

        if not news:
            self.logger.warning("RSS blocked → fallback HTML")
            news = self._fetch_trending()

        return news

    # -----------------------------
    def _fetch_rss(self) -> List[Dict]:

        try:
            res = self.scraper.get(
                self.RSS_URL,
                timeout=20,
                allow_redirects=True
            )
            res.raise_for_status()
        except Exception as e:
            self.logger.error("RSS fetch failed: %s", e)
            return []

        try:
            root = ET.fromstring(res.text)
        except Exception as e:
            self.logger.error("RSS parse failed: %s", e)
            return []

        items = root.findall(".//item")

        news_list = []

        for item in items[:3]:
            title = item.findtext("title", "").strip()
            link = item.findtext("link", "").strip()

            ticker = title.split(":")[0].strip()

            news_list.append({
                "id": link,
                "title": title,
                "tickers": [ticker],
            })

        self.logger.info("RSS fetched %d items", len(news_list))
        return news_list

    # -----------------------------
    def _fetch_trending(self) -> List[Dict]:

        try:
            res = self.scraper.get(
                self.TRENDING_URL,
                timeout=20,
                allow_redirects=True
            )
            res.raise_for_status()
        except Exception as e:
            self.logger.error("Trending fetch failed: %s", e)
            return []

        soup = BeautifulSoup(res.text, "html.parser")

        cards = soup.select("div.news-card")

        news_list = []

        for card in cards[:3]:
            try:
                symbol_tag = card.select_one("a.news-card-symbol")
                title_tag = card.select_one("a.news-card-title")

                ticker = symbol_tag.text.strip()
                title = title_tag.text.strip()
                link = title_tag["href"]

                if link.startswith("/"):
                    link = "https://www.stocktitan.net" + link

                news_list.append({
                    "id": link,
                    "title": title,
                    "tickers": [ticker],
                })

            except Exception:
                continue

        self.logger.info("HTML fetched %d items", len(news_list))
        return news_list
