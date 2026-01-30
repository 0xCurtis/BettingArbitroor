import json
from datetime import datetime, timezone
from typing import Dict, List

import requests

from config import POLYMARKET_API_URL, TARGET_MARKETS_PER_EXCHANGE
from logger import error_logger
from scrapers.base import BaseMarketScraper


# Push test
class PolymarketScraper(BaseMarketScraper):
    def __init__(self):
        super().__init__("Polymarket", POLYMARKET_API_URL)
        self.target_markets = TARGET_MARKETS_PER_EXCHANGE
        self.current_time = datetime.now(timezone.utc)

    def normalize_market(self, market: Dict) -> Dict | None:
        try:
            events = market.get("events")
            events_dict = []
            if events:
                all_expired = True
                for event in events:
                    end_date = event.get("endDate")
                    if end_date:
                        try:
                            dt_str = end_date.replace("Z", "+00:00")
                            dt = datetime.fromisoformat(dt_str)
                            if dt > self.current_time:
                                all_expired = False
                        except ValueError:
                            pass

                    events_dict.append(
                        {
                            "id": event.get("id"),
                            "title": event.get("title"),
                            "description": event.get("description"),
                            "end_date": event.get("endDate"),
                        }
                    )

                if all_expired and len(events) > 0:
                    return None

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

    def _fetch_page(self, offset: int = 0, limit: int = 100) -> tuple[List[Dict], int]:
        try:
            url = f"{self.api_url}&limit={limit}&offset={offset}&order=endDateIso&ascending=false"
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            if not isinstance(data, list):
                return [], 0

            raw_count = len(data)
            markets = []
            for market in data:
                normalized = self.normalize_market(market)
                if normalized:
                    markets.append(normalized)

            return markets, raw_count
        except (requests.RequestException, ValueError, KeyError) as e:
            error_logger.log_error(e, context=f"fetching {self.name} markets page")
            return [], 0

    def fetch_markets(self, limit: int = None) -> List[Dict]:
        self.current_time = datetime.now(timezone.utc)
        target = limit if limit is not None else self.target_markets
        all_markets = []
        offset = 0
        page_limit = 100
        max_iterations = (target // page_limit) * 3 + 50
        consecutive_empty_pages = 0
        max_empty_pages = 10
        total_raw = 0

        for iteration in range(max_iterations):
            if len(all_markets) >= target:
                break

            page_markets, raw_count = self._fetch_page(offset=offset, limit=page_limit)
            total_raw += raw_count

            if raw_count == 0:
                break

            if len(page_markets) == 0:
                consecutive_empty_pages += 1
                if consecutive_empty_pages >= max_empty_pages:
                    break
            else:
                consecutive_empty_pages = 0

            all_markets.extend(page_markets)
            offset += page_limit

            if raw_count < page_limit:
                break

        if target > 0 and len(all_markets) < target:
            print(
                f"  Warning: Only fetched {len(all_markets)}/{target} valid Polymarket markets "
                f"(fetched {total_raw} raw, {total_raw - len(all_markets)} filtered as expired)"
            )

        return all_markets[:target]
