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
            question = market.get("question", "")
            outcomes_str = market.get("outcomes", "[]")
            outcome_prices_str = market.get("outcomePrices", "[]")

            if not question:
                return None

            if isinstance(outcomes_str, str):
                outcomes = json.loads(outcomes_str)
            else:
                outcomes = outcomes_str

            if isinstance(outcome_prices_str, str):
                outcome_prices = json.loads(outcome_prices_str)
            else:
                outcome_prices = outcome_prices_str

            if not isinstance(outcomes, list) or not isinstance(outcome_prices, list):
                return None

            if len(outcomes) != len(outcome_prices):
                return None

            yes_index = None
            no_index = None

            for i, outcome in enumerate(outcomes):
                if isinstance(outcome, str):
                    outcome_upper = outcome.upper()
                    if outcome_upper == "YES":
                        yes_index = i
                    elif outcome_upper == "NO":
                        no_index = i

            if yes_index is None or no_index is None:
                return None

            yes_price = float(outcome_prices[yes_index])
            no_price = float(outcome_prices[no_index])

            if yes_price <= 0 or no_price <= 0:
                return None

            market_id = market.get("id", "")
            slug = market.get("events", {})[0].get("slug", "")
            url = f"https://polymarket.com/event/{slug}"

            return {
                "event": question,
                "yes_price": yes_price,
                "no_price": no_price,
                "source": self.name,
                "url": url,
            }
        except (KeyError, ValueError, TypeError, json.JSONDecodeError) as e:
            error_logger.log_error(e, context=f"normalizing {self.name} market")
            return None

    def _fetch_page(self, offset: int = 0, limit: int = 100) -> List[Dict]:
        try:
            url = f"{self.api_url.split('?')[0]}?limit={limit}&closed=false&offset={offset}"
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

