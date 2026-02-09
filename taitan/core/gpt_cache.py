# taitan/core/gpt_cache.py

import json
from pathlib import Path
from typing import Optional
from taitan.core.decision import Decision


class GPTCache:
    def __init__(self, cache_file: Path, logger):
        self.cache_file = cache_file
        self.logger = logger
        self._data = {}

        self._load()

    def _load(self):
        if self.cache_file.exists():
            try:
                self._data = json.loads(self.cache_file.read_text())
                self.logger.info("GPT cache loaded (%s items)", len(self._data))
            except Exception as e:
                self.logger.error("Failed to load GPT cache: %s", e)
                self._data = {}

    def save(self):
        self.cache_file.write_text(json.dumps(self._data, indent=2))

    def get(self, news_id: str) -> Optional[Decision]:
        item = self._data.get(news_id)
        if not item:
            return None

        return Decision(
            action=item["action"],
            ticker=item["ticker"],
            score=item["score"],
            reason=item["reason"],
        )

    def set(self, news_id: str, decision: Decision):
        self._data[news_id] = {
            "action": decision.action,
            "ticker": decision.ticker,
            "score": decision.score,
            "reason": decision.reason,
        }
        self.save()
