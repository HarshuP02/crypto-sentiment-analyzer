import sqlite3
from datetime import datetime

DB_NAME = "crypto_sentiment.db"

def init_db():
    """Initializes SQLite database tables for incoming crypto sentiment data."""
    conn = sqlite3.connect(DB_NAME)
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
    conn.close()

def insert_post(post_id, source, title, content, published_at, coin_tag):
    """Inserts a single raw post/article into the database."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("""
        INSERT OR IGNORE INTO crypto_posts 
        (id, source, title, content, published_at, coin_tag)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (post_id, source, title, content, published_at, coin_tag))
        conn.commit()
    except Exception as e:
        print(f"Error inserting record: {e}")
    finally:
        conn.close()

def get_unscored_posts():
    """Retrieves all posts that have not yet received a sentiment score."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, title, content FROM crypto_posts 
        WHERE sentiment_score IS NULL
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows

def update_sentiment_batch(updates):
    """
    Updates records with computed sentiment scores.
    updates: list of tuples (sentiment_score, sentiment_label, post_id)
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.executemany("""
        UPDATE crypto_posts 
        SET sentiment_score = ?, sentiment_label = ? 
        WHERE id = ?
    """, updates)
    conn.commit()
    conn.close()

def init_price_table():
    """Initializes table to store historical & current crypto price records."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS crypto_prices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        coin_tag TEXT,
        timestamp TIMESTAMP,
        open REAL,
        high REAL,
        low REAL,
        close REAL,
        volume REAL,
        UNIQUE(coin_tag, timestamp)
    )
    """)
    conn.commit()
    conn.close()

def insert_price_records(records):
    """
    Batch inserts or replaces price records.
    records: list of tuples (coin_tag, timestamp, open, high, low, close, volume)
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.executemany("""
    INSERT OR REPLACE INTO crypto_prices 
    (coin_tag, timestamp, open, high, low, close, volume)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, records)
    conn.commit()
    conn.close()