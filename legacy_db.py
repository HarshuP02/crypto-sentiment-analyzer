import sqlite3
from typing import List, Tuple, Optional

DB_NAME = "crypto_sentiment.db"

LABEL_MAPPING = {
    "positive": "BULLISH",
    "bullish": "BULLISH",
    "negative": "BEARISH",
    "bearish": "BEARISH",
    "neutral": "NEUTRAL"
}


def normalize_label(raw_label: str) -> str:
    """Normalizes raw sentiment labels to a unified format (BULLISH, BEARISH, NEUTRAL)."""
    if not isinstance(raw_label, str):
        return "NEUTRAL"
    return LABEL_MAPPING.get(raw_label.lower().strip(), "NEUTRAL")


def init_db() -> None:
    """Initializes SQLite database tables for incoming crypto sentiment data."""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS crypto_posts (
            id TEXT PRIMARY KEY,
            source TEXT,
            title TEXT,
            content TEXT,
            published_at TIMESTAMP,
            coin_tag TEXT,
            sentiment_score REAL,
            sentiment_label TEXT
        )
        """)
        conn.commit()


def insert_post(
    post_id: str,
    source: str,
    title: str,
    content: str,
    published_at: str,
    coin_tag: str
) -> None:
    """Inserts a single raw post/article into the database."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT OR IGNORE INTO crypto_posts 
            (id, source, title, content, published_at, coin_tag)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (post_id, source, title, content, published_at, coin_tag))
            conn.commit()
    except Exception as e:
        print(f"Error inserting record: {e}")


def get_unscored_posts() -> List[Tuple[str, str, str]]:
    """Retrieves all posts that have not yet received a sentiment score."""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, title, content FROM crypto_posts 
            WHERE sentiment_score IS NULL
        """)
        return cursor.fetchall()


def update_sentiment_batch(updates: List[Tuple[float, str, str]]) -> None:
    """
    Updates records with computed sentiment scores and normalized labels.
    updates: list of tuples (sentiment_score, raw_sentiment_label, post_id)
    """
    # Enforce label unification before writing to DB
    normalized_updates = [
        (float(score), normalize_label(label), str(post_id))
        for score, label, post_id in updates
    ]
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.executemany("""
            UPDATE crypto_posts 
            SET sentiment_score = ?, sentiment_label = ? 
            WHERE id = ?
        """, normalized_updates)
        conn.commit()


def init_price_table() -> None:
    """Initializes table to store historical & current crypto price records."""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS crypto_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            coin_tag TEXT NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL,
            UNIQUE(coin_tag, timestamp)
        )
        """)
        conn.commit()


def insert_price_records(records: List[Tuple[str, str, float, float, float, float, float]]) -> None:
    """
    Batch inserts or replaces price records.
    records: list of tuples (coin_tag, timestamp, open, high, low, close, volume)
    """
    if not records:
        return
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.executemany("""
        INSERT OR REPLACE INTO crypto_prices 
        (coin_tag, timestamp, open, high, low, close, volume)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, records)
        conn.commit()