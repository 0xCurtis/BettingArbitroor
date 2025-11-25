import json
import os

from scrapers.kalshi import KalshiScraper
from scrapers.polymarket import PolymarketScraper


def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)


def save_markets(markets, filename):
    with open(filename, "w") as f:
        json.dump(markets, f, indent=4)
    print(f"Saved {len(markets)} markets to {filename}")


def main():
    data_dir = "testing_data"
    ensure_dir(data_dir)

    # Initialize scrapers
    kalshi = KalshiScraper()
    polymarket = PolymarketScraper()

    # Define tasks: (scraper, limit, filename)
    tasks = [
        (kalshi, 25, "kalshi_25.json"),
        (polymarket, 25, "polymarket_25.json"),
        (kalshi, 1000, "kalshi_1000.json"),
        (polymarket, 1000, "polymarket_1000.json"),
    ]

    for scraper, count, filename in tasks:
        print(f"Fetching {count} markets from {scraper.get_name()}...")
        try:
            markets = scraper.fetch_markets(limit=count)
            filepath = os.path.join(data_dir, filename)
            save_markets(markets, filepath)
        except Exception as e:
            print(f"Error fetching data for {filename}: {e}")


if __name__ == "__main__":
    main()
