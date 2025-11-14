from typing import Dict, List

from config import ARBITRAGE_THRESHOLD
from scrapers.base import BaseMarketScraper


class ArbitrageFinder:
    def __init__(self, scrapers: List[BaseMarketScraper], threshold: float = ARBITRAGE_THRESHOLD):
        self.scrapers = scrapers
        self.threshold = threshold

    def find_opportunities(self, markets_by_source: Dict[str, List[Dict]]) -> List[Dict]:
        opportunities = []
        sources = list(markets_by_source.keys())
        if len(sources) < 2:
            return opportunities
        return opportunities

    def _events_match(self, event1: str, event2: str) -> bool:
        return event1 == event2
