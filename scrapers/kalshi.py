from typing import Any, Dict, List

import requests

from config import KALSHI_API_URL, TARGET_MARKETS_PER_EXCHANGE
from logger import error_logger
from scrapers.base import BaseMarketScraper


class KalshiScraper(BaseMarketScraper):
    def __init__(self):
        super().__init__("Kalshi", KALSHI_API_URL)
        self.target_markets = TARGET_MARKETS_PER_EXCHANGE

    def normalize_market(self, market: Dict) -> Dict | None:
        try:
            event_ticker = market.get("event_ticker", "")
            title = market.get("title", "")
            
            yes_bid_dollars = market.get("yes_bid_dollars")
            yes_ask_dollars = market.get("yes_ask_dollars")
            no_bid_dollars = market.get("no_bid_dollars")
            no_ask_dollars = market.get("no_ask_dollars")
            
            if yes_bid_dollars is None or yes_ask_dollars is None or no_bid_dollars is None or no_ask_dollars is None:
                return None
            
            yes_bid = float(yes_bid_dollars)
            yes_ask = float(yes_ask_dollars)
            no_bid = float(no_bid_dollars)
            no_ask = float(no_ask_dollars)

            if yes_bid <= 0 or yes_ask <= 0 or no_bid <= 0 or no_ask <= 0:
                return None

            yes_price = (yes_bid + yes_ask) / 2
            no_price = (no_bid + no_ask) / 2

            mve_collection_ticker = market.get("mve_collection_ticker")
            ticker = market.get("ticker", event_ticker)

            if mve_collection_ticker:
                url = f"https://kalshi.com/markets/{mve_collection_ticker}"
            elif event_ticker:
                url = f"https://kalshi.com/markets/{event_ticker}"
            elif ticker:
                url = f"https://kalshi.com/markets/{ticker}"
            else:
                url = ""

            return {
                "event": title or event_ticker,
                "yes_price": yes_price,
                "no_price": no_price,
                "ticker": event_ticker,
                "source": self.name,
                "url": url,
            }
        except (KeyError, ValueError, TypeError) as e:
            error_logger.log_error(e, context=f"normalizing {self.name} market")
            return None

    def _fetch_page(self, cursor: str = None, limit: int = 100) -> tuple[List[Dict], str | None]:
        try:
            url = f"{self.api_url}?limit={limit}"
            if cursor:
                url += f"&cursor={cursor}"

            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            markets = []
            markets_list = data.get("markets", [])
            for market in markets_list:
                normalized = self.normalize_market(market)
                if normalized:
                    markets.append(normalized)

            next_cursor = data.get("cursor")
            return markets, next_cursor
        except (requests.RequestException, ValueError, KeyError) as e:
            error_logger.log_error(e, context=f"fetching {self.name} markets page")
            return [], None

    def fetch_markets(self) -> List[Dict]:
        try:
            return self._fetch_page(limit=self.target_markets)
        except Exception as e:
            error_logger.log_error(e, context=f"fetching {self.name} markets")
            return []


