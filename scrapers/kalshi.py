from datetime import datetime, timezone
from typing import Dict, List

import requests

from config import KALSHI_API_URL, TARGET_MARKETS_PER_EXCHANGE
from logger import error_logger
from scrapers.base import BaseMarketScraper


class KalshiScraper(BaseMarketScraper):
    def __init__(self):
        super().__init__("Kalshi", KALSHI_API_URL)
        self.target_markets = TARGET_MARKETS_PER_EXCHANGE
        self.current_time = datetime.now(timezone.utc)

    def normalize_market(self, market: Dict) -> Dict | None:
        try:
            close_time = market.get("close_time")
            if close_time:
                # Handle 'Z' if present, though Python 3.11+ supports it directly in fromisoformat
                # We use replace just to be safe across minor versions if strictly < 3.11
                dt_str = close_time.replace("Z", "+00:00")
                dt = datetime.fromisoformat(dt_str)
                if dt < self.current_time:
                    return None

            return {
                "close_time": close_time,
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

    def _fetch_page(
        self,
        cursor: str = None,
        limit: int = 100,
        min_close_ts: int = None,
        max_close_ts: int = None,
    ) -> tuple[List[Dict], str | None]:
        try:
            url = f"{self.api_url}?limit={limit}"
            if cursor:
                url += f"&cursor={cursor}"
            if min_close_ts is not None:
                url += f"&min_close_ts={min_close_ts}"
            if max_close_ts is not None:
                url += f"&max_close_ts={max_close_ts}"

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

    def fetch_markets(
        self, limit: int = None, min_close_ts: int = None, max_close_ts: int = None
    ) -> List[Dict]:
        self.current_time = datetime.now(timezone.utc)
        target = limit if limit is not None else self.target_markets
        try:
            markets, next_cursor = self._fetch_page(
                limit=target, min_close_ts=min_close_ts, max_close_ts=max_close_ts
            )
            while len(markets) < target and next_cursor:
                new_markets, next_cursor = self._fetch_page(
                    cursor=next_cursor,
                    limit=target,
                    min_close_ts=min_close_ts,
                    max_close_ts=max_close_ts,
                )
                markets.extend(new_markets)
            return markets[:target]
        except Exception as e:
            error_logger.log_error(e, context=f"fetching {self.name} markets")
            return []
