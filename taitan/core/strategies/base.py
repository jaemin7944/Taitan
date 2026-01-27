from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from taitan.core.decision import Decision


class BaseStrategy(ABC):
    def __init__(self, config: dict, logger):
        self.config = config
        self.logger = logger

    @abstractmethod
    def evaluate(self, news_list: List[Dict]) -> Optional[Decision]:
        pass
