from abc import ABC, abstractmethod
from typing import Dict


class BaseNotifier(ABC):
    @abstractmethod
    def notify_arbitrage(self, opportunity: Dict) -> None:
        pass

    @abstractmethod
    def notify_status(self, message: str) -> None:
        pass

    @abstractmethod
    def notify_summary(self, markets_checked: Dict[str, int], opportunities_found: int) -> None:
        pass

