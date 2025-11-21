import json
from typing import Dict, List

import requests

from config import POLYMARKET_API_URL, TARGET_MARKETS_PER_EXCHANGE
from logger import error_logger
from scrapers.base import BaseMarketScraper


class PolymarketScraper(BaseMarketScraper):
    def __init__(self):
        super().__init__("Polymarket", POLYMARKET_API_URL)
        self.target_markets = TARGET_MARKETS_PER_EXCHANGE

    def normalize_market(self, market: Dict) -> Dict | None:
        try:
            events = market.get("events")
            if events:
                events_dict = []
                for event in events:
                    events_dict.append({
                        "id": event.get("id"),
                        "title": event.get("title"),
                        "description": event.get("description"),
                        "end_date": event.get("endDate"),
                    })
            return {
                "id": market.get("id"),
                "question": market.get("question"),
                "description": market.get("description"),
                "slug": market.get("slug"),
                "events": events_dict,
            }
        except (KeyError, ValueError, TypeError, json.JSONDecodeError) as e:
            error_logger.log_error(e, context=f"normalizing {self.name} market")
            return None

    def _fetch_page(self, offset: int = 0, limit: int = 100) -> List[Dict]:
        try:
            url = f"{self.api_url}&limit={limit}&offset={offset}"
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            if not isinstance(data, list):
                return []

            markets = []
            for market in data:
                normalized = self.normalize_market(market)
                if normalized:
                    markets.append(normalized)

            return markets
        except (requests.RequestException, ValueError, KeyError) as e:
            error_logger.log_error(e, context=f"fetching {self.name} markets page")
            return []

    def fetch_markets(self) -> List[Dict]:
        all_markets = []
        offset = 0
        limit = 100
        max_iterations = (self.target_markets // limit) + 10

        for _ in range(max_iterations):
            if len(all_markets) >= self.target_markets:
                break

            page_markets = self._fetch_page(offset=offset, limit=limit)

            if not page_markets:
                break

            all_markets.extend(page_markets)
            offset += limit

            if len(page_markets) < limit:
                break

        return all_markets[:self.target_markets]



if __name__ == "__main__":
    scraper = PolymarketScraper()
    markets = scraper.fetch_markets()
    # Only dump the 10 first markets
    markets = markets[:10]
    with open("polymarket_markets.json", "w") as f:
        json.dump(markets, f, indent=4)