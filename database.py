import sqlite3
from datetime import datetime, timedelta
from typing import Dict

from logger import error_logger


class ArbitrageDatabase:
    def __init__(self, db_path: str = "arbitrage.db"):
        self.db_path = db_path
        self._init_database()

    def _init_database(self) -> None:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS arbitrage_opportunities (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event TEXT NOT NULL,
                        source1 TEXT NOT NULL,
                        price1 REAL NOT NULL,
                        source2 TEXT NOT NULL,
                        price2 REAL NOT NULL,
                        url1 TEXT,
                        url2 TEXT,
                        spread REAL NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(event, source1, price1, source2, price2)
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_event_sources
                    ON arbitrage_opportunities(event, source1, source2)
                    """
                )
                conn.commit()
        except sqlite3.Error as e:
            error_logger.log_error(e, context="initializing database")

    def opportunity_exists(self, opportunity: Dict) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM arbitrage_opportunities
                    WHERE event = ? AND source1 = ? AND price1 = ?
                    AND source2 = ? AND price2 = ?
                    """,
                    (
                        opportunity["event"],
                        opportunity["source1"],
                        opportunity["price1"],
                        opportunity["source2"],
                        opportunity["price2"],
                    ),
                )
                result = cursor.fetchone()
                return result[0] > 0 if result else False
        except sqlite3.Error as e:
            error_logger.log_error(e, context="checking if opportunity exists")
            return False

    def add_opportunity(self, opportunity: Dict) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO arbitrage_opportunities
                    (event, source1, price1, source2, price2, url1, url2, spread)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        opportunity["event"],
                        opportunity["source1"],
                        opportunity["price1"],
                        opportunity["source2"],
                        opportunity["price2"],
                        opportunity.get("url1", ""),
                        opportunity.get("url2", ""),
                        opportunity["spread"],
                    ),
                )
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            error_logger.log_error(e, context="adding opportunity to database")
            return False

    def cleanup_old_opportunities(self, days: int = 7) -> int:
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    DELETE FROM arbitrage_opportunities
                    WHERE created_at < ?
                    """,
                    (cutoff_date.isoformat(),),
                )
                conn.commit()
                return cursor.rowcount
        except sqlite3.Error as e:
            error_logger.log_error(e, context="cleaning up old opportunities")
            return 0

    def get_opportunity_count(self) -> int:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM arbitrage_opportunities")
                result = cursor.fetchone()
                return result[0] if result else 0
        except sqlite3.Error as e:
            error_logger.log_error(e, context="getting opportunity count")
            return 0

