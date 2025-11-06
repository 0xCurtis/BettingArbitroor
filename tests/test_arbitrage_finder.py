from arbitrage_finder import ArbitrageFinder


def test_calculate_spread():
    finder = ArbitrageFinder([])
    assert abs(finder.calculate_spread(0.50, 0.60) - 0.10) < 0.0001
    assert abs(finder.calculate_spread(0.60, 0.50) - 0.10) < 0.0001
    assert finder.calculate_spread(0.50, 0.50) == 0.00


def test_find_opportunities():
    finder = ArbitrageFinder([])

    markets_by_source = {
        "Polymarket": [
            {
                "event": "Will Trump win the 2024 U.S. presidential election?",
                "yes_price": 0.58,
                "no_price": 0.42,
                "source": "Polymarket",
            }
        ],
        "Kalshi": [
            {
                "event": "Will Trump win 2024 election?",
                "yes_price": 0.65,
                "no_price": 0.35,
                "source": "Kalshi",
            }
        ],
    }

    opportunities = finder.find_opportunities(markets_by_source)

    assert len(opportunities) > 0
    opp = opportunities[0]
    assert opp["spread"] > 0.04
    assert opp["price1"] == 0.58
    assert opp["price2"] == 0.65


def test_events_match():
    finder = ArbitrageFinder([])

    assert finder._events_match("trump win election", "trump election win")
    assert finder._events_match("bitcoin price", "bitcoin price target")
    assert not finder._events_match("trump election", "bitcoin price")

