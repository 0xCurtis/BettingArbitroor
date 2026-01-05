# finder.py
import time
from typing import List

from config import FETCH_INTERVAL_SECONDS, OLLAMA_CLI, OLLAMA_MODEL, OLLAMA_OPTIONS, OLLAMA_URL, OLLAMA_AUTH
from database import MatchDatabase
from logger import error_logger
from scrapers.base import BaseMarketScraper
from scrapers.kalshi import KalshiScraper
from scrapers.polymarket import PolymarketScraper
import requests

class MarketMappingBot:
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
                {"role": "user", "content": "What is the capital of France?"}
            ],
            "stream": False
        }
        headers = {
            "Authorization": f"Bearer {OLLAMA_AUTH}"
        }
        chat_resp = requests.post(f"{OLLAMA_URL}/ollama/v1/generate", json=chat_payload, headers=headers, timeout=60)
        chat_resp.raise_for_status()

    def run(self) -> None:
        print("Starting Market Mapping Bot...")

        self.test_ollama_connection()

        while True:
            try:
                print("Fetching market data...", end="", flush=True)
                poly_markets = []
                kalshi_markets = []

                for scraper in self.scrapers:
                    markets: List[dict] = scraper.fetch_markets()
                    name: str = scraper.get_name()
                    if name == "Polymarket":
                        poly_markets = markets
                    elif name == "Kalshi":
                        kalshi_markets = markets
                print(f" Done ({len(poly_markets)} Poly, {len(kalshi_markets)} Kalshi)")

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
