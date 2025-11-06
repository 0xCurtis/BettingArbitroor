### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager

### Installation

1. Install dependencies:
```bash
uv sync
```

2. Install development dependencies (optional, for testing):
```bash
uv sync --extra dev
```

## Usage

Run the arbitrage finder:

```bash
uv run python finder.py
```

The script will:
- Fetch market data from both Polymarket and Kalshi every 10 seconds
- Compare prices for matched markets
- Print arbitrage opportunities when the spread exceeds 4% (configurable in `config.py`)
- Continue running until interrupted with `Ctrl+C`

## Configuration

Edit `config.py` to customize

## Testing

Run tests with pytest:

```bash
uv run pytest -v
```

## Linting

Check code quality with ruff:

```bash
uv run ruff check .
```

## Logging

- You have 3 Logging sources available (Console, Telegram, Discord) by default Discord and Console are enabled.

## Notes

- This tool only **detects** arbitrage opportunities; it does not execute trades
- Market matching uses a simple manual mapping - can be improved with fuzzy matching or NLP
- API endpoints may require authentication for production use
- Handle rate limiting appropriately for production deployments

