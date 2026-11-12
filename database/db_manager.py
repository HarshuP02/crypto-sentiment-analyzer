from datetime import datetime, timedelta, timezone
import pandas as pd
from sqlalchemy import create_engine, text
from config import DATABASE_URL


class DatabaseManager:
    def __init__(self, db_url: str | None = None):
        # Use explicit argument or the resolved DATABASE_URL from config.py
        self.db_url = db_url or DATABASE_URL

        if self.db_url:
            if self.db_url.startswith("postgres://"):
                self.db_url = self.db_url.replace("postgres://", "postgresql+psycopg2://", 1)
            elif self.db_url.startswith("postgresql://") and not self.db_url.startswith("postgresql+"):
                self.db_url = self.db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

            self.engine = create_engine(self.db_url, pool_pre_ping=True)
            self.db_type = "postgresql"
        else:
            self.sqlite_path = "crypto_sentiment.db"
            self.db_url = f"sqlite:///{self.sqlite_path}"
            self.engine = create_engine(self.db_url)
            self.db_type = "sqlite"

        self.init_schema()

    def get_posts_by_timeframe(self, ticker: str, hours: int = 24) -> pd.DataFrame:
        """Fetches posts within the trailing look-back window (works on both Postgres & SQLite)."""
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=hours)
        query = text("""
            SELECT published_at, source, aspect, score, label, title
            FROM sentiment_posts
            WHERE ticker = :ticker
              AND published_at >= :cutoff
            ORDER BY published_at DESC;
        """)
        return pd.read_sql(query, self.engine, params={"ticker": ticker, "cutoff": cutoff})

    def init_schema(self):
        """Initializes tables for posts and aggregated hourly signals."""
        queries = [
            """
            CREATE TABLE IF NOT EXISTS sentiment_posts (
                post_hash VARCHAR(64) PRIMARY KEY,
                source VARCHAR(32),
                ticker VARCHAR(16),
                title TEXT,
                aspect VARCHAR(32),
                score REAL,
                label VARCHAR(16),
                published_at TIMESTAMP
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS hourly_signals (
                id VARCHAR(64) PRIMARY KEY,
                timestamp TIMESTAMP,
                ticker VARCHAR(16),
                close_price REAL,
                avg_sentiment REAL,
                signal VARCHAR(32)
            );
            """
        ]
        with self.engine.begin() as conn:
            for q in queries:
                conn.execute(text(q))

    def insert_post(
        self,
        post_hash: str,
        source: str,
        ticker: str,
        title: str,
        aspect: str,
        score: float,
        label: str,
        published_at: str
    ):
        """Inserts a single post, ignoring duplicates based on hash."""
        if self.db_type == "postgresql":
            stmt = text("""
                INSERT INTO sentiment_posts (post_hash, source, ticker, title, aspect, score, label, published_at)
                VALUES (:hash, :source, :ticker, :title, :aspect, :score, :label, :pub)
                ON CONFLICT (post_hash) DO NOTHING;
            """)
        else:
            stmt = text("""
                INSERT OR IGNORE INTO sentiment_posts (post_hash, source, ticker, title, aspect, score, label, published_at)
                VALUES (:hash, :source, :ticker, :title, :aspect, :score, :label, :pub);
            """)

        with self.engine.begin() as conn:
            conn.execute(stmt, {
                "hash": post_hash,
                "source": source,
                "ticker": ticker,
                "title": title,
                "aspect": aspect,
                "score": score,
                "label": label,
                "pub": published_at
            })

    def get_recent_posts(
        self,
        ticker: str | None = None,
        limit: int = 500,
        since: str | None = None
    ) -> pd.DataFrame:
        """Fetches sentiment records for a specific asset (or all assets if ticker is None)."""
        conditions = []
        params: dict = {"limit": limit}

        if ticker:
            conditions.append("ticker = :ticker")
            params["ticker"] = ticker

        if since:
            if self.db_type == "postgresql":
                conditions.append("published_at >= CAST(:since AS TIMESTAMP)")
            else:
                conditions.append("published_at >= :since")
            params["since"] = since

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        query = text(f"""
            SELECT published_at, ticker, source, aspect, score, label, title
            FROM sentiment_posts
            {where_clause}
            ORDER BY published_at DESC
            LIMIT :limit;
        """)
        return pd.read_sql(query, self.engine, params=params)