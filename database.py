import sqlite3
from typing import Dict, List, Optional
from logger import error_logger

class MatchDatabase:
    def __init__(self, db_path: str = "market_matches.db"):
        self.db_path = db_path
        self._init_database()

    def _init_database(self) -> None:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # Table for storing established matches between Polymarket and Kalshi
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS market_matches (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        polymarket_slug TEXT NOT NULL,
                        polymarket_event TEXT NOT NULL,
                        kalshi_ticker TEXT NOT NULL,
                        kalshi_event TEXT NOT NULL,
                        confidence_score REAL,
                        is_verified BOOLEAN DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(polymarket_slug, kalshi_ticker)
                    )
                    """
                )
                conn.commit()
        except sqlite3.Error as e:
            error_logger.log_error(e, context="initializing database")

    def match_exists(self, poly_slug: str, kalshi_ticker: str) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT 1 FROM market_matches WHERE polymarket_slug = ? AND kalshi_ticker = ?", 
                    (poly_slug, kalshi_ticker)
                )
                return cursor.fetchone() is not None
        except sqlite3.Error as e:
            error_logger.log_error(e, context="checking match existence")
            return False

    def save_match(self, poly_market: Dict, kalshi_market: Dict, confidence: float) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO market_matches 
                    (polymarket_slug, polymarket_event, kalshi_ticker, kalshi_event, confidence_score)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        # We need to ensure we pass the slug/ticker. 
                        # Using URL or ID if specific fields aren't in the normalized dict yet.
                        poly_market.get("url", "").split("/")[-1], # Extract slug from URL as fallback
                        poly_market["event"],
                        kalshi_market.get("ticker", ""),
                        kalshi_market["event"],
                        confidence
                    ),
                )
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            error_logger.log_error(e, context="saving match")
            return False

    def get_verified_matches(self) -> List[Dict]:
        """Retrieve all matches that have been verified (or all if we treat high confidence as verified)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM market_matches ORDER BY created_at DESC")
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            error_logger.log_error(e, context="fetching matches")
            return []
