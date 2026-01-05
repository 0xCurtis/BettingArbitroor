# config.py
ARBITRAGE_THRESHOLD = 0.04

FETCH_INTERVAL_SECONDS = 60

TARGET_MARKETS_PER_EXCHANGE = 500

POLYMARKET_API_URL = "https://gamma-api.polymarket.com/markets?closed=false"
KALSHI_API_URL = (
    "https://api.elections.kalshi.com/trade-api/v2/markets?status=open&mve_filter=exclude"
)

TOP_K_CANDIDATES = 2
MIN_SIMILARITY = 0.35

AUTO_ACCEPT_THRESHOLD = 0.88
AUTO_REJECT_THRESHOLD = 0.60
JACCARD_MIN_FOR_AUTO_ACCEPT = 0.30

# Ollama settings
OLLAMA_URL = "http://57.131.25.126"
OLLAMA_MODEL = "llama3"
OLLAMA_AUTH = "98cdb0a6-ddec-47e8-b454-70cc79e3b3be"
# Runtime options sent to Ollama; tune for your hardware
OLLAMA_OPTIONS = {
    "num_ctx": 512,
    "num_predict": 64,
    "temperature": 0.1,
}

# Optional CLI fallback (when HTTP API paths are unavailable)
OLLAMA_CLI = "ollama"
