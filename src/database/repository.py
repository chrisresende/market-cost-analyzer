import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime

class MarketRepository:
    def __init__(self, db_path: str = "data/market_history.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS market_quotes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    ticker TEXT NOT NULL,
                    name TEXT NOT NULL,
                    price REAL NOT NULL,
                    currency TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(date, ticker)
                )
            """)
            conn.commit()

    def save_quote(self, ticker: str, name: str, price: float, currency: str = "BRL"):
        today = datetime.now().strftime("%Y-%m-%d")
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO market_quotes (date, ticker, name, price, currency)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(date, ticker) DO UPDATE SET price=excluded.price
            """, (today, ticker, name, price, currency))
            conn.commit()

    def get_history(self, ticker: str, limit: int = 30) -> pd.DataFrame:
        with sqlite3.connect(self.db_path) as conn:
            query = """
                SELECT date, price FROM market_quotes 
                WHERE ticker = ? ORDER BY date DESC LIMIT ?
            """
            df = pd.read_sql_query(query, conn, params=(ticker, limit))
            return df.sort_values("date")
