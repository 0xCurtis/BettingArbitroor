from typing import Dict

from notifiers.base import BaseNotifier


class ConsoleNotifier(BaseNotifier):
    def notify_arbitrage(self, opportunity: Dict) -> None:
        event = opportunity["event"]
        source1 = opportunity["source1"]
        price1 = opportunity["price1"]
        source2 = opportunity["source2"]
        price2 = opportunity["price2"]
        spread_pct = opportunity["spread"] * 100

        if price1 < price2:
            buy_source = source1
            buy_price = price1
            sell_source = source2
            sell_price = price2
        else:
            buy_source = source2
            buy_price = price2
            sell_source = source1
            sell_price = price1

        print(f"\n🚨 Arbitrage detected: {event}")
        print(f"Buy on {buy_source} at {buy_price:.2f}")
        print(f"Sell on {sell_source} at {sell_price:.2f}")
        print(f"Spread: {spread_pct:.2f}%\n")

    def notify_status(self, message: str) -> None:
        print(message)

    def notify_summary(self, markets_checked: Dict[str, int], opportunities_found: int) -> None:
        if opportunities_found == 0:
            market_list = [f"{count} {name}" for name, count in markets_checked.items()]
            market_counts = ", ".join(market_list)
            print(f"✓ No arbitrage opportunities found (checked {market_counts} markets)")

