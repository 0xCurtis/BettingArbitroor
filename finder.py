# finder.py
import json
import os
import time
from datetime import datetime
from typing import List, Optional

import requests

from config import FETCH_INTERVAL_SECONDS, OLLAMA_AUTH, OLLAMA_MODEL, OLLAMA_URL
from database import MatchDatabase
from logger import error_logger
from scrapers.base import BaseMarketScraper
from scrapers.kalshi import KalshiScraper
from scrapers.polymarket import PolymarketScraper


class MarketMappingBot:
    MIN_PREDICTIONS = 5000

    def __init__(self, scrapers: List[BaseMarketScraper], interval: int = FETCH_INTERVAL_SECONDS):
        from matcher.matcher import MarketMatcher

        self.scrapers = scrapers
        self.matcher = MarketMatcher()
        self.interval = interval
        self.db = MatchDatabase()

    def test_ollama_connection(self) -> None:
        chat_payload = {
            "model": OLLAMA_MODEL,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "What is the capital of France?"},
            ],
            "stream": False,
        }
        headers = {"Authorization": f"Bearer {OLLAMA_AUTH}"}
        chat_resp = requests.post(
            f"{OLLAMA_URL}/v1/generate", json=chat_payload, headers=headers, timeout=60
        )
        chat_resp.raise_for_status()

    def _dump_markets_to_json(self, poly_markets: List[dict], kalshi_markets: List[dict]) -> None:
        """Dump retrieved markets to JSON files for testing purposes."""
        data_dir = "runtime"
        os.makedirs(data_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        poly_file = os.path.join(data_dir, f"polymarket_runtime_{timestamp}.json")
        kalshi_file = os.path.join(data_dir, f"kalshi_runtime_{timestamp}.json")

        with open(poly_file, "w") as f:
            json.dump(poly_markets, f, indent=2)
        print(f"  Dumped {len(poly_markets)} Polymarket markets to {poly_file}")

        with open(kalshi_file, "w") as f:
            json.dump(kalshi_markets, f, indent=2)
        print(f"  Dumped {len(kalshi_markets)} Kalshi markets to {kalshi_file}")

    def _extract_polymarket_date_range(
        self, poly_markets: List[dict]
    ) -> tuple[Optional[int], Optional[int]]:
        end_dates = []
        for market in poly_markets:
            events = market.get("events", [])
            for event in events:
                end_date_str = event.get("end_date")
                if end_date_str:
                    try:
                        dt_str = end_date_str.replace("Z", "+00:00")
                        dt = datetime.fromisoformat(dt_str)
                        end_dates.append(dt)
                    except (ValueError, AttributeError):
                        pass

        if not end_dates:
            return None, None

        min_end_date = min(end_dates)
        max_end_date = max(end_dates)

        min_close_ts = int(min_end_date.timestamp())
        max_close_ts = int(max_end_date.timestamp())

        return min_close_ts, max_close_ts

    def run(self) -> None:
        print("Starting Market Mapping Bot...")

        self.test_ollama_connection()

        while True:
            try:
                print("Fetching market data...", end="", flush=True)

                poly_markets = []
                kalshi_markets = []
                kalshi_scraper = None

                for scraper in self.scrapers:
                    name: str = scraper.get_name()
                    if name == "Polymarket":
                        markets: List[dict] = scraper.fetch_markets(limit=self.MIN_PREDICTIONS)
                        poly_markets = markets
                    elif name == "Kalshi":
                        kalshi_scraper = scraper

                min_close_ts, max_close_ts = self._extract_polymarket_date_range(poly_markets)
                if kalshi_scraper:
                    kalshi_markets = kalshi_scraper.fetch_markets(
                        limit=self.MIN_PREDICTIONS,
                        min_close_ts=min_close_ts,
                        max_close_ts=max_close_ts,
                    )

                total_pairs = len(poly_markets) * len(kalshi_markets)
                print(f" Total pairs: {total_pairs:,}")

                matches = self.matcher.find_matches(poly_markets, kalshi_markets)

                for poly, kalshi, conf in matches:
                    if self.db.save_match(poly, kalshi, conf):
                        print(
                            f"NEW MATCH: {poly['event']} ⚡ {kalshi['event']} "
                            f"(Confidence: {conf:.2f})"
                        )

            except KeyboardInterrupt:
                print("\nStopping bot...")
                break
            except Exception as e:
                error_logger.log_error(e, context="main mapping loop")
            print(
                "Next fetch at",
                time.strftime("%H:%M:%S", time.localtime(time.time() + self.interval)),
            )
            time.sleep(self.interval)


def main() -> None:
    try:
        print("Creating scrapers...")
        scrapers = [
            PolymarketScraper(),
            KalshiScraper(),
        ]
        print("Scrapers created successfully")
        bot = MarketMappingBot(scrapers, interval=60)
        bot.run()
    except Exception as e:
        print(f"Error in main(): {e}")
        import traceback

        traceback.print_exc()
        raise


if __name__ == "__main__":
    print("Starting main...")
    main()
