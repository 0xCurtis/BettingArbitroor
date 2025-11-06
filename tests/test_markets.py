from scrapers.kalshi import KalshiScraper
from scrapers.polymarket import PolymarketScraper


def test_normalize_polymarket_market():
    scraper = PolymarketScraper()
    market = {
        "question": "Will Trump win the 2024 U.S. presidential election?",
        "outcomes": '["Yes", "No"]',
        "outcomePrices": '["0.58", "0.42"]',
    }

    result = scraper.normalize_market(market)
    assert result is not None
    assert result["event"] == "Will Trump win the 2024 U.S. presidential election?"
    assert result["yes_price"] == 0.58
    assert result["no_price"] == 0.42
    assert result["source"] == "Polymarket"


def test_normalize_polymarket_market_invalid():
    scraper = PolymarketScraper()
    market = {
        "question": "Test",
        "outcomes": [],
    }

    result = scraper.normalize_market(market)
    assert result is None


def test_normalize_kalshi_market():
    scraper = KalshiScraper()
    market = {
        "event_ticker": "TRUMP24",
        "title": "Will Trump win 2024 election?",
        "yes_bid": 0.60,
        "yes_ask": 0.65,
        "no_bid": 0.35,
        "no_ask": 0.40,
    }

    result = scraper.normalize_market(market)
    assert result is not None
    assert result["event"] == "Will Trump win 2024 election?"
    assert result["yes_price"] == 0.625
    assert result["no_price"] == 0.375
    assert result["ticker"] == "TRUMP24"
    assert result["source"] == "Kalshi"


def test_normalize_kalshi_market_invalid():
    scraper = KalshiScraper()
    market = {
        "event_ticker": "TEST",
        "yes_bid": 0,
        "yes_ask": 0,
    }

    result = scraper.normalize_market(market)
    assert result is None
