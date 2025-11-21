# finder.py
import time
from typing import List

from config import FETCH_INTERVAL_SECONDS, OLLAMA_CLI, OLLAMA_MODEL
from database import MatchDatabase
from logger import error_logger
from matcher import MarketMatcher
from scrapers.base import BaseMarketScraper
from scrapers.kalshi import KalshiScraper
from scrapers.polymarket import PolymarketScraper


class MarketMappingBot:
    def __init__(
        self, scrapers: List[BaseMarketScraper], interval: int = FETCH_INTERVAL_SECONDS
    ):
        self.scrapers = scrapers
        self.matcher = MarketMatcher()
        self.interval = interval
        self.db = MatchDatabase()

    def test_ollama_connection(self) -> None:
        try:
            import requests
            import subprocess

            ok = False
            try:
                resp = requests.get(f"{self.matcher.ollama_url}/api/tags", timeout=3)
                ok = ok or (resp.status_code == 200)
            except Exception:
                pass
            if not ok:
                try:
                    resp = requests.get(
                        f"{self.matcher.ollama_url}/v1/models", timeout=3
                    )
                    ok = ok or (resp.status_code == 200)
                except Exception:
                    pass
            if not ok:
                try:
                    subprocess.run(
                        [OLLAMA_CLI, "--version"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=3,
                        check=True,
                    )
                    ok = True
                    print(f"✓ Using Ollama CLI fallback (model: {OLLAMA_MODEL})")
                except Exception:
                    pass
            if ok:
                print(
                    f"✓ Connected to LLM at {self.matcher.ollama_url} or CLI (model: {self.matcher.model})"
                )
                self.matcher.llm_enabled = True
            else:
                print("No LLM endpoint or CLI found. Disabling LLM.")
                self.matcher.llm_enabled = False
        except Exception:
            print("LLM preflight failed. Disabling LLM verification.")
            self.matcher.llm_enabled = False

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
                            f"NEW MATCH: {poly['event']} ⚡ {kalshi['event']} (Confidence: {conf:.2f})"
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
    scrapers = [
        PolymarketScraper(),
        KalshiScraper(),
    ]

    bot = MarketMappingBot(scrapers, interval=60)
    bot.run()


if __name__ == "__main__":
    main()
