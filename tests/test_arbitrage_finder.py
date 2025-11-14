from arbitrage_finder import ArbitrageFinder


def test_calculate_spread():
    finder = ArbitrageFinder([])
    assert abs(finder.calculate_spread(0.50, 0.60) - 0.10) < 0.0001
    assert abs(finder.calculate_spread(0.60, 0.50) - 0.10) < 0.0001
    assert finder.calculate_spread(0.50, 0.50) == 0.00


def test_find_opportunities():
    finder = ArbitrageFinder([])
    markets_by_source = {}
    opportunities = finder.find_opportunities(markets_by_source)

    assert len(opportunities) > 0
    print(opportunities)