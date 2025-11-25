import json

from scrapers.polymarket import PolymarketScraper

if __name__ == "__main__":
    scraper = PolymarketScraper()
    print("Scraper initialized")
    print("Fetching 10 markets for testing...")
    # Fetch a small number for quick testing
    markets = scraper.fetch_markets(limit=10)
    print(f"Markets fetched: {len(markets)}")

    # Dump to local file for inspection
    with open("polymarket_markets.json", "w") as f:
        json.dump(markets, f, indent=4)
    print("Dumped to polymarket_markets.json")
