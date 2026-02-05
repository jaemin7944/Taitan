import json
from typing import Optional, List, Dict
from openai import OpenAI

from taitan.core.decision import Decision
from taitan.core.strategies.base import BaseStrategy


class GPTNewsStrategy(BaseStrategy):
    def __init__(self, config: dict, logger):
        super().__init__(config, logger)
        self.client = OpenAI(api_key=config["openai"]["api_key"])
        self.model = config["openai"].get("model", "gpt-4o-mini")

    def evaluate(self, news_list: List[Dict]) -> Optional[Decision]:
        if not news_list:
            return Decision(
                action="HOLD",
                ticker=None,
                score=0.0,
                reason="no news",
            )

        prompt = self._build_prompt(news_list)

        try:
            res = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a US stock trading assistant."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
            )

            content = res.choices[0].message.content
            self.logger.info("GPT raw response: %s", content)

            data = json.loads(content)

            return Decision(
                action=data.get("action", "HOLD"),
                ticker=data.get("ticker"),
                score=float(data.get("score", 0.0)),
                reason=data.get("reason", ""),
            )

        except Exception as e:
            self.logger.error("GPT strategy failed: %s", e)
            return Decision(
                action="HOLD",
                ticker=None,
                score=0.0,
                reason="GPT error",
            )

    def _build_prompt(self, news_list: List[Dict]) -> str:
        lines = []
        for n in news_list:
            lines.append(
                f"- ticker: {n.get('ticker')} | title: {n.get('title')}"
            )

        return f"""
You are given top 3 breaking US stock news.

News:
{chr(10).join(lines)}

Pick the SINGLE most attractive stock to BUY.
If none is attractive, choose HOLD.

Return ONLY valid JSON in the following format:
{{
  "action": "BUY" or "HOLD",
  "ticker": "AAPL" or null,
  "score": 0.0 ~ 1.0,
  "reason": "short explanation"
}}
"""
