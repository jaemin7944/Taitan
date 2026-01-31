# taitan/data/market.py
from typing import Optional

class Market:
    def __init__(self, kis_client, logger):
        self.kis = kis_client
        self.logger = logger

    def get_current_price(self, ticker: str) -> Optional[float]:
        res = self.kis.get(
            path="/uapi/overseas-price/v1/quotations/price",
            tr_id="FHKST01010100",
            params={
                "FID_COND_MRKT_DIV_CODE": "J",   # 해외주식
                "FID_INPUT_ISCD": ticker.upper()
            },
        )

        output = res.get("output")
        if not output:
            self.logger.error(f"Response received but 'output' is missing: {res}")
            return None 

        # 한투 해외주식 현재가 필드 우선순위
        # 1. last: 현재가 (정규장 중에는 이 값이 메인)
        # 2. p_last: 프리/애프터마켓 현재가
        # 3. base: 전일 종가 (장 시작 전 기준가)

        last = output.get("last")
        p_last = output.get("p_last")
        base = output.get("base")   

        # 값이 있고 0보다 큰지 확인하는 함수
        def valid(v):
            try: return float(v) if v and float(v) > 0 else None
            except: return None 

        # 정규장 중이면 last, 그 외 시간은 p_last, 둘 다 없으면 base 사용
        price = valid(last) or valid(p_last) or valid(base) 

        if price:
            return price    

        self.logger.warning(f"No valid price found in output fields for {ticker}")
        return None

#     def get_current_price(self, ticker: str) -> Optional[float]:

#         res = self.kis.get(
#             path="/uapi/overseas-price/v1/quotations/price",
#             tr_id="FHKST01010100",
#             params={
#                 "EXCD": "NAS",
#                 "SYMB": ticker,
#             },
#         )   

#         if "output1" in res and "last" in res["output1"]:
#             return float(res["output1"]["last"])    

#         if "output" in res and "last" in res["output"]:
#             return float(res["output"]["last"]) 

#         # 장외 / 시세 없음
#         self.logger.info("No price available (market closed)")
#         return None

    
    

