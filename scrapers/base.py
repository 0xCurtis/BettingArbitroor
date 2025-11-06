from abc import ABC, abstractmethod
from typing import Dict, List


class BaseMarketScraper(ABC):
    def __init__(self, name: str, api_url: str, timeout: int = 10):
        self.name = name
        self.api_url = api_url
        self.timeout = timeout

    @abstractmethod
    def normalize_market(self, market: Dict) -> Dict | None:
        pass

    @abstractmethod
    def fetch_markets(self) -> List[Dict]:
        pass

    def get_name(self) -> str:
        return self.name

