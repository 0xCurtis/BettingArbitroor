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

1.  Fetch: It scrapes the latest active markets from Polymarket and Kalshi.
2.  Match: Two‑stage "retrieval + verification" pipeline in `matcher.MarketMatcher`:
    - Stage 1 — Retrieval: Find top‑K likely pairs via vector search. If `sentence-transformers` and `faiss-cpu` are present, cosine similarity over embeddings is used. Otherwise, a fast token‑based inverted index prunes candidates (still avoids O(N²)).
    - Stage 2 — Verification: Run the LLM only on those candidates (default K=5). A greedy pass locks in confirmed matches and skips later checks that involve already‑matched items.
3.  Save: Confirmed matches (LLM confidence ≥ 0.70) are saved to a local SQLite database (`market_matches.db`).

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

## Optional Speedups (Embeddings + FAISS)

The retrieval stage automatically upgrades to vector embeddings if the libraries are present:

- `sentence-transformers`
- `faiss-cpu`

If these are not installed, the matcher uses a token‑based inverted index that still avoids the O(N²) cross‑product.

Install optional extras (example with uv):

```bash
uv add sentence-transformers faiss-cpu
```

LLM setup (Ollama)
- Install Ollama and pull a small model that fits your system:
  - `ollama pull llama3.2:3b`  (Meta Llama 3.2 3B; instruction tuned by default)
  - Or a quantized 8B: `ollama pull llama3:8b-instruct-q4_0`
- Start the server: `ollama serve`
- The bot will try Ollama’s HTTP API; if not available, it will fall back to the `ollama` CLI automatically.

## Roadmap

- [x] Basic LLM matcher using Ollama
- [ ] Optimize the pre-filter to avoid sending obvious mismatches to Ollama (saves time but optional atp)
- [ ] Implement the arbitrage calculator that uses the `market_matches.db` table
- [ ] Add support for more exchanges (e.g., Betfair, PredictIt) (we will hit a time complexity wall and new arb strats there)
- [ ] Build a simple web dashboard to view active arbitrage opportunities (because why not flask is cool but can become pretty messy to handle in the same repo)
