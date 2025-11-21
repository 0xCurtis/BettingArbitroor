BEFORE ANYTHING ELSE SUMMIMASEN GUDFIT SAMA I DIDN'T TOOK THE TIME TO MAKE A PROPER DOCKERFILE CUZ MUH TESTING AND DOCKER=SLOW


# Most of this README is AI generated and proof-read by me.

# Market Mapping Bot

A tool to find and link identical prediction markets between Polymarket and Kalshi. It uses a local LLM (Ollama) to intelligently match events even when they have different titles or phrasing.

## Setup

### 1. Install uv
We use `uv` for fast Python package management.
- **Mac/Linux**: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **Windows**: `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`

### 2. Install Ollama
The bot needs a local LLM server to compare market titles.
- **Mac/Linux**: Run `curl -fsSL https://ollama.com/install.sh | sh`
- **Windows**: Download the installer from [ollama.com](https://ollama.com)

After installing, pull the model we use (llama3):
```bash
ollama pull llama3
ollama serve
```
ollama serve keeps Ollama running in the background.

### 3. Install Dependencies
Sync the project environment:

```bash
uv sync
```

## How It Works

The bot runs in a continuous loop (defined in `finder.py`):

1.  **Fetch**: It scrapes the latest active markets from Polymarket and Kalshi.
2.  **Match**: It sends pairs of markets to your local Ollama instance. The `MarketMatcher` class constructs a prompt that includes the event titles, rules, and descriptions. It asks the LLM to verify if they represent the exact same real-world outcome (checking dates, entities, and conditions).
3.  **Save**: Confirmed matches (confidence > 70%) are saved to a local SQLite database (`market_matches.db`).

## Running the Bot

To start the persistent background job:

```bash
uv run python finder.py
```

It will print a log of what it is checking. When it finds a match, it will alert you in the console.

To run the test script with sample data:

```bash
uv run python test_matcher_demo.py
```

## Roadmap

- [x] Basic LLM matcher using Ollama
- [ ] Optimize the pre-filter to avoid sending obvious mismatches to Ollama (saves time but optional atp)
- [ ] Implement the arbitrage calculator that uses the `market_matches.db` table
- [ ] Add support for more exchanges (e.g., Betfair, PredictIt) (we will hit a time complexity wall and new arb strats there)
- [ ] Build a simple web dashboard to view active arbitrage opportunities (because why not flask is cool but can become pretty messy to handle in the same repo)
