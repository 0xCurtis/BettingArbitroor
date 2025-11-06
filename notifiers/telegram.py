from typing import Dict

from notifiers.base import BaseNotifier


class TelegramNotifier(BaseNotifier):
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id

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

        _message = (
            f"🚨 *Arbitrage Detected*\n\n"
            f"*Event:* {event}\n"
            f"*Buy on:* {buy_source} at {buy_price:.2f}\n"
            f"*Sell on:* {sell_source} at {sell_price:.2f}\n"
            f"*Spread:* {spread_pct:.2f}%"
        )
        # TODO: Implement Telegram API call using self.bot_token and self.chat_id
        # Example:
        # url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        # requests.post(url, json={"chat_id": self.chat_id, "text": _message})

    def notify_status(self, message: str) -> None:
        pass

    def notify_summary(self, markets_checked: Dict[str, int], opportunities_found: int) -> None:
        pass

