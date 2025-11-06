import json
from typing import Dict, List

import requests

from config import POLYMARKET_API_URL
from logger import error_logger
from scrapers.base import BaseMarketScraper


class PolymarketScraper(BaseMarketScraper):
    def __init__(self):
        super().__init__("Polymarket", POLYMARKET_API_URL)

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

            return {
                "event": question,
                "yes_price": yes_price,
                "no_price": no_price,
                "source": self.name,
            }
        except (KeyError, ValueError, TypeError, json.JSONDecodeError) as e:
            error_logger.log_error(e, context=f"normalizing {self.name} market")
            return None

    def fetch_markets(self) -> List[Dict]:
        try:
            response = requests.get(self.api_url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            markets = []
            for market in data:
                normalized = self.normalize_market(market)
                if normalized:
                    markets.append(normalized)

            return markets
        except (requests.RequestException, ValueError, KeyError) as e:
            error_logger.log_error(e, context=f"fetching {self.name} markets")
            return []

