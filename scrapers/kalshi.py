from typing import Dict, List

import requests

from config import KALSHI_API_URL
from logger import error_logger
from scrapers.base import BaseMarketScraper


class KalshiScraper(BaseMarketScraper):
    def __init__(self):
        super().__init__("Kalshi", KALSHI_API_URL)

    def normalize_market(self, market: Dict) -> Dict | None:
        try:
            event_ticker = market.get("event_ticker", "")
            title = market.get("title", "")
            yes_bid = float(market.get("yes_bid", 0))
            yes_ask = float(market.get("yes_ask", 0))
            no_bid = float(market.get("no_bid", 0))
            no_ask = float(market.get("no_ask", 0))

            if yes_bid <= 0 or yes_ask <= 0 or no_bid <= 0 or no_ask <= 0:
                return None

            yes_mid = (yes_bid + yes_ask) / 2
            no_mid = (no_bid + no_ask) / 2

            return {
                "event": title or event_ticker,
                "yes_price": yes_mid,
                "no_price": no_mid,
                "ticker": event_ticker,
                "source": self.name,
            }
        except (KeyError, ValueError, TypeError) as e:
            error_logger.log_error(e, context=f"normalizing {self.name} market")
            return None

    def fetch_markets(self) -> List[Dict]:
        try:
            response = requests.get(self.api_url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            markets = []
            markets_list = data.get("markets", [])
            for market in markets_list:
                normalized = self.normalize_market(market)
                if normalized:
                    markets.append(normalized)
            return markets
        except (requests.RequestException, ValueError, KeyError) as e:
            error_logger.log_error(e, context=f"fetching {self.name} markets")
            return []

