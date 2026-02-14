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
    
        link = news_list[0].get("link")
        if not link:
            return None
    
        parts = link.split("/")
        # ... /news/DBGI/...
        if "news" in parts:
            idx = parts.index("news")
            if len(parts) > idx + 1:
                return parts[idx + 1].upper()
    
        return None
    

    @abstractmethod
    def evaluate(self, news_list: List[Dict]) -> Optional[Decision]:
        pass
