import time
from typing import List

from config import FETCH_INTERVAL_SECONDS
from database import MatchDatabase
from logger import error_logger
from matcher import MarketMatcher
from scrapers.base import BaseMarketScraper
from scrapers.kalshi import KalshiScraper
from scrapers.polymarket import PolymarketScraper


class MarketMappingBot:
    def __init__(
        self,
        scrapers: List[BaseMarketScraper],
        interval: int = FETCH_INTERVAL_SECONDS
    ):
        self.scrapers = scrapers
        self.matcher = MarketMatcher()
        self.interval = interval
        self.db = MatchDatabase()

    def test_ollama_connection(self) -> None:
        try:
            import requests
            resp = requests.get(f"{self.matcher.ollama_url}/api/tags")
            if resp.status_code == 200:
                print(f"✓ Connected to Ollama ({self.matcher.model})")
            else:
                print(f"⚠️  Ollama responded with status {resp.status_code}")
        except Exception:
            print("❌ Could not connect to Ollama. Is it running?")
            raise Exception("Could not connect to Ollama")

    def run(self) -> None:
        print("Starting Market Mapping Bot...")
        
        self.test_ollama_connection()

        while True:
            try:
                print("Fetching market data...", end="", flush=True)
                poly_markets = []
                kalshi_markets = []
                
                for scraper in self.scrapers:
                    markets : List[dict] = scraper.fetch_markets()
                    name : str = scraper.get_name()
                    
                    # Debugging to ensure we're getting the correct markets in the right format
                    if name == "Polymarket":
                        poly_markets = markets
                    elif name == "Kalshi":
                        kalshi_markets = markets
                print(f" Done ({len(poly_markets)} Poly, {len(kalshi_markets)} Kalshi)")
                
                matches = self.matcher.find_matches(poly_markets, kalshi_markets)
                
                for poly, kalshi, conf in matches:
                    if self.db.save_match(poly, kalshi, conf):
                        print(f"🚨 NEW MATCH: {poly['event']} ⚡ {kalshi['event']} (Confidence: {conf:.2f})")
                
            except KeyboardInterrupt:
                print("\nStopping bot...")
                break
            except Exception as e:
                error_logger.log_error(e, context="main mapping loop")
            print("Next fetch at", time.strftime("%H:%M:%S", time.localtime(time.time() + self.interval)))
            time.sleep(self.interval)


def main() -> None:
    scrapers = [
        PolymarketScraper(),
        KalshiScraper(),
    ]

    bot = MarketMappingBot(scrapers, interval=60) # 1 minute for dev
    bot.run()


if __name__ == "__main__":
    main()
