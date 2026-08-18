import yfinance as yf
import pandas as pd
from datetime import datetime
from database import init_price_table, insert_price_records

# Mapping ticker symbols to Yahoo Finance pairs
COIN_TICKER_MAP = {
    "BTC": "BTC-USD",
    "ETH": "ETH-USD",
    "SOL": "SOL-USD"
}


def fetch_and_store_crypto_prices(period="7d", interval="1h"):
    """
    Fetches historical OHLCV data for tracked coins and persists to SQLite.
    """
    init_price_table()
    print("📈 Fetching live & historical market prices via yfinance...")

    for coin_tag, ticker in COIN_TICKER_MAP.items():
        try:
            asset = yf.Ticker(ticker)
            df = asset.history(period=period, interval=interval)

            if df.empty:
                print(f"⚠️ No price data found for {ticker}")
                continue

            records = []
            for index, row in df.iterrows():
                # Format timestamp string: YYYY-MM-DD HH:00:00
                ts_str = index.strftime('%Y-%m-%d %H:%M:%S')
                records.append((
                    coin_tag,
                    ts_str,
                    round(float(row['Open']), 2),
                    round(float(row['High']), 2),
                    round(float(row['Low']), 2),
                    round(float(row['Close']), 2),
                    round(float(row['Volume']), 2)
                ))

            insert_price_records(records)
            print(f" -> Stored {len(records)} price candles for {coin_tag}")
        except Exception as e:
            print(f"❌ Failed to fetch market data for {coin_tag}: {e}")


def get_merged_sentiment_price_data(coin_tag="BTC"):
    """
    Merges hourly average sentiment scores with hourly price candles.
    """
    import sqlite3
    conn = sqlite3.connect("crypto_sentiment.db")

    # Query price history
    price_query = """
        SELECT timestamp, close, volume 
        FROM crypto_prices 
        WHERE coin_tag = ? 
        ORDER BY timestamp ASC
    """
    df_prices = pd.read_sql_query(price_query, conn, params=(coin_tag,))

    # Query aggregated hourly sentiment
    sentiment_query = """
        SELECT strftime('%Y-%m-%d %H:00:00', published_at) as timestamp,
               AVG(sentiment_score) as avg_sentiment,
               COUNT(*) as post_volume
        FROM crypto_posts
        WHERE coin_tag = ? AND sentiment_score IS NOT NULL
        GROUP BY strftime('%Y-%m-%d %H:00:00', published_at)
        ORDER BY timestamp ASC
    """
    df_sentiment = pd.read_sql_query(sentiment_query, conn, params=(coin_tag,))
    conn.close()

    if df_prices.empty:
        return pd.DataFrame()

    # Convert timestamps and perform left join
    df_prices['timestamp'] = pd.to_datetime(df_prices['timestamp'])
    if not df_sentiment.empty:
        df_sentiment['timestamp'] = pd.to_datetime(df_sentiment['timestamp'])
        merged_df = pd.merge(df_prices, df_sentiment, on='timestamp', how='left')
        merged_df['avg_sentiment'] = merged_df['avg_sentiment'].fillna(0.0)
        merged_df['post_volume'] = merged_df['post_volume'].fillna(0)
    else:
        merged_df = df_prices
        merged_df['avg_sentiment'] = 0.0
        merged_df['post_volume'] = 0

    return merged_df