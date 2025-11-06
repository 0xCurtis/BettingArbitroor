from typing import Dict, List

from config import ARBITRAGE_THRESHOLD
from scrapers.base import BaseMarketScraper


class ArbitrageFinder:
    def __init__(self, scrapers: List[BaseMarketScraper], threshold: float = ARBITRAGE_THRESHOLD):
        self.scrapers = scrapers
        self.threshold = threshold

    def calculate_spread(self, price1: float, price2: float) -> float:
        return abs(price1 - price2)

    def find_opportunities(self, markets_by_source: Dict[str, List[Dict]]) -> List[Dict]:
        opportunities = []
        sources = list(markets_by_source.keys())

        if len(sources) < 2:
            return opportunities

        for i, source1 in enumerate(sources):
            for source2 in sources[i + 1:]:
                markets1 = markets_by_source[source1]
                markets2 = markets_by_source[source2]

                for market1 in markets1:
                    event1 = market1.get("event", "").lower()
                    price1 = market1.get("yes_price", 0)

                    for market2 in markets2:
                        event2 = market2.get("event", "").lower()
                        price2 = market2.get("yes_price", 0)

                        if self._events_match(event1, event2):
                            spread = self.calculate_spread(price1, price2)

                            if spread > self.threshold:
                                opportunities.append({
                                    "event": market1.get("event", ""),
                                    "source1": source1,
                                    "price1": price1,
                                    "source2": source2,
                                    "price2": price2,
                                    "spread": spread,
                                })

        return opportunities

    def _events_match(self, event1: str, event2: str) -> bool:
        event1_words = set(event1.lower().split())
        event2_words = set(event2.lower().split())

        if not event1_words or not event2_words:
            return False

        common_words = event1_words.intersection(event2_words)
        if len(common_words) == 0:
            return False

        similarity = len(common_words) / max(len(event1_words), len(event2_words))
        return similarity >= 0.3

