from typing import Any, Dict, List

import requests

from config import KALSHI_API_URL, TARGET_MARKETS_PER_EXCHANGE
from logger import error_logger
from scrapers.base import BaseMarketScraper
import json

class KalshiScraper(BaseMarketScraper):
    def __init__(self):
        super().__init__("Kalshi", KALSHI_API_URL)
        self.target_markets = TARGET_MARKETS_PER_EXCHANGE

    def normalize_market(self, market: Dict) -> Dict | None:
        try:
            return {
                "close_time": market.get("close_time"),
                "created_time": market.get("created_time"),
                "early_close_condition": market.get("early_close_condition"),
                "rules_primary": market.get("rules_primary"),
                "rules_secondary": market.get("rules_secondary"),
                "slug": market.get("slug"),
                "title": market.get("title"),
                "ticker": market.get("ticker"),

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
            markets, next_cursor = self._fetch_page(limit=self.target_markets)
            while len(markets) < self.target_markets and next_cursor:
                new_markets, next_cursor = self._fetch_page(cursor=next_cursor, limit=self.target_markets)
                markets.extend(new_markets)
            return markets[:self.target_markets]
        except Exception as e:
            error_logger.log_error(e, context=f"fetching {self.name} markets")
            return []



if __name__ == "__main__":
    scraper = KalshiScraper()
    print("scrapper initialized")
    print("fetching markets...")
    markets = scraper.fetch_markets()
    print(f"markets fetched: {len(markets)}")
    # Only dump the 10 first markets
    markets = markets[:10]
    print(f"Dumping {len(markets)} markets to kalshi_markets.json")
    with open("kalshi_markets.json", "w") as f:
        json.dump(markets, f, indent=4)