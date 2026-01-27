from dataclasses import dataclass
from typing import Optional


@dataclass
class Decision:
    action: str               # "BUY" | "SELL" | "HOLD"
    ticker: Optional[str]     # 예: "AAPL"
    reason: str               # 판단 이유
    score: float = 0.0        # 우선순위/강도
