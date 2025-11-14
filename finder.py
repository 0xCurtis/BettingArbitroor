import time
from typing import List

from arbitrage_finder import ArbitrageFinder
from config import ARBITRAGE_THRESHOLD, FETCH_INTERVAL_SECONDS
from database import ArbitrageDatabase
from logger import error_logger
from notifiers.base import BaseNotifier
from notifiers.console import ConsoleNotifier
from scrapers.base import BaseMarketScraper
from scrapers.kalshi import KalshiScraper
from scrapers.polymarket import PolymarketScraper


class ArbitrageBot:
    def __init__(
        self,
        scrapers: List[BaseMarketScraper],
        notifiers: List[BaseNotifier],
        threshold: float = ARBITRAGE_THRESHOLD,
        interval: int = FETCH_INTERVAL_SECONDS,
        db_path: str = "arbitrage.db",
    ):
        self.scrapers = scrapers
        self.notifiers = notifiers
        self.finder = ArbitrageFinder(scrapers, threshold)
        self.interval = interval
        self.db = ArbitrageDatabase(db_path)

    def run(self) -> None:
        self.db.cleanup_old_opportunities(days=7)
        existing_count = self.db.get_opportunity_count()

        for notifier in self.notifiers:
            notifier.notify_status("Starting arbitrage finder...")
            notifier.notify_status(f"Monitoring every {self.interval} seconds")
            notifier.notify_status(f"Arbitrage threshold: {self.finder.threshold * 100:.1f}%")
            notifier.notify_status(f"Database: {existing_count} existing opportunities tracked\n")

        while True:
            try:
                markets_by_source = {}
                for scraper in self.scrapers:
                    markets = scraper.fetch_markets()
                    if scraper.get_name() == "Kalshi" and markets:
                        markets_by_source[scraper.get_name()] = markets[0]
                    else:
                        markets_by_source[scraper.get_name()] = markets
                all_markets_valid = all(markets for markets in markets_by_source.values())
                if not all_markets_valid:
                    for notifier in self.notifiers:
                        notifier.notify_status("⚠️  Skipping cycle: failed to fetch market data")
                    time.sleep(self.interval)
                    continue

                opportunities = self.finder.find_opportunities(markets_by_source)

                if opportunities:
                    new_opportunities = []
                    for opp in opportunities:
                        if not self.db.opportunity_exists(opp):
                            if self.db.add_opportunity(opp):
                                new_opportunities.append(opp)
                                for notifier in self.notifiers:
                                    notifier.notify_arbitrage(opp)

                    if new_opportunities:
                        skipped = len(opportunities) - len(new_opportunities)
                        for notifier in self.notifiers:
                            notifier.notify_status(
                                f"Found {len(new_opportunities)} new arbitrage "
                                f"opportunities (skipped {skipped} duplicates)"
                            )
                else:
                    markets_checked = {
                        name: len(markets) for name, markets in markets_by_source.items()
                    }
                    for notifier in self.notifiers:
                        notifier.notify_summary(markets_checked, 0)

            except KeyboardInterrupt:
                for notifier in self.notifiers:
                    notifier.notify_status("\n\nStopping arbitrage finder...")
                break
            except Exception as e:
                error_logger.log_error(e, context="main monitoring loop")

            time.sleep(self.interval)


def main() -> None:
    scrapers = [
        PolymarketScraper(),
        KalshiScraper(),
    ]

    notifiers = [
        ConsoleNotifier(),
        # DiscordNotifier(webhook_url="https://discord.com/api/webhooks/1435940084116361308/yB5TKeMHRV7TcXVh3_LY8UU9qqjrCvLcsey8fkL64A4UNK97caMIgLEP1qFt0YjXGEq1"),
    ]

    bot = ArbitrageBot(scrapers, notifiers)
    bot.run()


if __name__ == "__main__":
    main()
