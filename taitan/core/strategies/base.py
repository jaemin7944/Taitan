from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from taitan.core.decision import Decision


class BaseStrategy(ABC):
    def __init__(self, config: dict, logger):
        self.config = config
        self.logger = logger

    def peek_ticker(self, news_list):
        if not news_list:
            return None
        first = news_list[0]
        tickers = first.get("tickers", [])
        return tickers[0] if tickers else None

    @abstractmethod
    def evaluate(self, news_list: List[Dict]) -> Optional[Decision]:
        pass
