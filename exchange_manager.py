
import pybithumb
import pyupbit
import logging
from typing import Optional, Dict, Tuple, Any

logger = logging.getLogger(__name__)

class ExchangeManager:
    """
    Exchange Abstraction Layer
    Supports: Bithumb, Upbit
    """
    
    def __init__(self, exchange_name: str, access_key: str, secret_key: str):
        self.exchange_name = exchange_name.lower()
        self.access_key = access_key
        self.secret_key = secret_key
        self.client: Any = None
        
        self._initialize_client()
        
    def _initialize_client(self):
        try:
            if self.exchange_name == 'bithumb':
                self.client = pybithumb.Bithumb(self.access_key, self.secret_key)
            elif self.exchange_name == 'upbit':
                self.client = pyupbit.Upbit(self.access_key, self.secret_key)
            else:
                raise ValueError(f"Unsupported exchange: {self.exchange_name}")
            logger.info(f"✅ Exchange Client Initialized: {self.exchange_name.upper()}")
        except Exception as e:
            logger.error(f"❌ Failed to initialize exchange client: {e}")
            self.client = None

    def get_ohlcv(self, ticker: str, interval: str = "day") -> Optional[Any]:
        """
        Get OHLCV data
        standardize ticker to 'BTC' (no prefix)
        """
        try:
            if self.exchange_name == 'bithumb':
                # pybithumb defaults to daily if interval not specified or "time"
                # it supports: "24h", "12h", "6h", "1h", "30m", "10m", "5m", "3m", "1m"
                # mapping "day" to "24h"
                if interval == "day":
                    return pybithumb.get_ohlcv(ticker)
                
                # if needed, map other intervals. 
                # For now, default usage is daily.
                return pybithumb.get_ohlcv(ticker)
                
            elif self.exchange_name == 'upbit':
                u_ticker = f"KRW-{ticker}"
                u_interval = "day" if interval == "day" else interval
                # pyupbit intervals: day, minute1, minute3, etc.
                return pyupbit.get_ohlcv(u_ticker, interval=u_interval, count=200)
                
        except Exception as e:
            logger.error(f"❌ OHLCV Error ({self.exchange_name}): {e}")
            return None

    def get_current_price(self, ticker: str) -> Optional[float]:
        """
        현재 가격 조회 (캐싱 적용)
        """
        import time
        
        # 🔥 캐시 확인 (5초 유효)
        if not hasattr(self, '_price_cache'):
            self._price_cache = {}
        
        cache_key = ticker
        now = time.time()
        
        if cache_key in self._price_cache:
            cached_price, cached_time = self._price_cache[cache_key]
            if now - cached_time < 5:  # 5초 이내면 캐시 사용
                return cached_price
        
        # API 호출
        try:
            if self.exchange_name == 'bithumb':
                price = pybithumb.get_current_price(ticker)
            elif self.exchange_name == 'upbit':
                price = pyupbit.get_current_price(f"KRW-{ticker}")
            else:
                return None
            
            # 캐시 저장
            if price:
                self._price_cache[cache_key] = (price, now)
            
            return price
            
        except Exception as e:
            logger.debug(f"⚠️ Price Error ({self.exchange_name}): {e}")
            return None
    
    def get_orderbook_bid_price(self, ticker: str) -> Optional[float]:
        """
        매수 1호가 조회 (시장가 매도 시 실제 체결 가격)
        업비트는 시장가 매도 시 '주문 수량 × 매수 1호가'로 계산
        """
        try:
            if self.exchange_name == 'upbit':
                orderbook = pyupbit.get_orderbook(f"KRW-{ticker}")
                if orderbook and 'orderbook_units' in orderbook:
                    # 매수 1호가 (가장 높은 매수 주문 가격)
                    bid_price = orderbook['orderbook_units'][0]['bid_price']
                    return float(bid_price)
            elif self.exchange_name == 'bithumb':
                # Bithumb도 유사하게 구현 가능 (pybithumb.get_orderbook 사용)
                return self.get_current_price(ticker)  # Fallback
        except Exception as e:
            logger.error(f"❌ Orderbook Error ({self.exchange_name}): {e}")
            return None

    def get_balance(self, ticker: str) -> Dict:
        """
        Get Balance
        Returns:
            {
                "krw_balance": float,
                "coin_balance": float,
                "total_assets": float
            }
        """
        try:
            if self.exchange_name == 'bithumb':
                # pybithumb.get_balance returns tuple: (btc_total, btc_in_use, krw_total, krw_in_use) ? 
                # Actually earlier code handled tuple/dict.
                # Standard pybithumb.get_balance("BTC") -> (total_coin, total_krw, in_use_coin, in_use_krw)
                balance = self.client.get_balance(ticker)
                if isinstance(balance, tuple):
                     return {
                        "krw_balance": balance[2], # total krw
                        "coin_balance": balance[0], # total coin
                        "total_assets": balance[2] + (balance[0] * self.get_current_price(ticker) or 0)
                    }
                return {"krw_balance": 0, "coin_balance": 0, "total_assets": 0}

            elif self.exchange_name == 'upbit':
                krw_balance = self.client.get_balance("KRW")
                if krw_balance is None:
                    krw_balance = 0.0
                    
                coin_balance = self.client.get_balance(f"KRW-{ticker}")
                if coin_balance is None:
                    coin_balance = 0.0
                    
                current_price = self.get_current_price(ticker)
                
                if current_price is None:
                    current_price = 0.0

                return {
                    "krw_balance": krw_balance,
                    "coin_balance": coin_balance,
                    "total_assets": krw_balance + (coin_balance * current_price)
                }
                
        except Exception as e:
            logger.error(f"❌ Balance Error ({self.exchange_name}): {e}")
            return {"krw_balance": 0, "coin_balance": 0, "total_assets": 0}

    def buy_market_order(self, ticker: str, amount_krw: float, amount_unit: float = 0) -> Any:
        try:
            if self.exchange_name == 'bithumb':
                if amount_unit <= 0:
                     price = self.get_current_price(ticker)
                     if price:
                         amount_unit = amount_krw / price
                     else:
                         return None
                
                result = self.client.buy_market_order(ticker, amount_unit)
                # Bithumb 응답 검증
                if isinstance(result, tuple) and result[0] == 'error':
                    logger.error(f"❌ Bithumb Buy Error: {result}")
                    return None
                return result
                
            elif self.exchange_name == 'upbit':
                result = self.client.buy_market_order(f"KRW-{ticker}", amount_krw)
                
                # 🛡️ Upbit 응답 검증: 에러 응답인지 확인
                if result is None:
                    logger.error("❌ Upbit Buy Order returned None")
                    return None
                if isinstance(result, dict) and 'error' in result:
                    error_msg = result['error'].get('message', str(result))
                    logger.error(f"❌ Upbit Buy Error: {error_msg}")
                    print(error_msg)  # 터미널에도 출력
                    return None
                
                logger.info(f"✅ Buy Order Success: {result.get('uuid', 'N/A')}")
                return result
                
        except Exception as e:
            logger.error(f"❌ Buy Order Error ({self.exchange_name}): {e}")
            return None

    def sell_market_order(self, ticker: str, volume: float) -> Any:
        try:
            if self.exchange_name == 'bithumb':
                result = self.client.sell_market_order(ticker, volume)
                # Bithumb 응답 검증
                if isinstance(result, tuple) and result[0] == 'error':
                    logger.error(f"❌ Bithumb Sell Error: {result}")
                    return None
                return result
                
            elif self.exchange_name == 'upbit':
                result = self.client.sell_market_order(f"KRW-{ticker}", volume)
                
                # 🛡️ Upbit 응답 검증: 에러 응답인지 확인
                if result is None:
                    logger.error("❌ Upbit Sell Order returned None")
                    return None
                if isinstance(result, dict) and 'error' in result:
                    error_msg = result['error'].get('message', str(result))
                    logger.error(f"❌ Upbit Sell Error: {error_msg}")
                    print(error_msg)  # 터미널에도 출력
                    return None
                
                logger.info(f"✅ Sell Order Success: {result.get('uuid', 'N/A')}")
                return result
                
        except Exception as e:
            logger.error(f"❌ Sell Order Error ({self.exchange_name}): {e}")
            return None

    def get_tickers(self) -> list:
        try:
            if self.exchange_name == 'bithumb':
                 # 🔥 빗썸: KRW 마켓만 명시적으로 요청
                 return pybithumb.get_tickers(payment_currency="KRW")
            elif self.exchange_name == 'upbit':
                # 🔥 업비트: KRW 마켓만 이중 필터링
                tickers = pyupbit.get_tickers(fiat="KRW")
                return [t.replace('KRW-', '') for t in tickers if t.startswith('KRW-')]
        except Exception as e:
            logger.error(f"❌ Failed to get tickers: {e}")
            return []

    def get_holdings(self) -> list:
        """
        보유 중인 모든 코인 잔고 조회 (KRW 제외)
        Returns:
            [{"ticker": "BTC", "amount": 1.5, "avg_buy_price": 50000000}, ...]
        """
        holdings = []
        try:
            if self.exchange_name == 'upbit':
                balances = self.client.get_balances()
                for b in balances:
                    currency = b['currency']
                    if currency == 'KRW': continue
                    
                    amount = float(b['balance']) # Available balance only to ensure tradeability
                    avg_price = float(b['avg_buy_price'])
                    
                    if amount > 0:
                        holdings.append({
                            "ticker": currency,
                            "amount": amount,
                            "avg_buy_price": avg_price
                        })
                        
            elif self.exchange_name == 'bithumb':
                # Bithumb: fallback not fully implemented yet
                pass
                
        except Exception as e:
            logger.error(f"❌ Failed to get holdings: {e}")
            
        return holdings
