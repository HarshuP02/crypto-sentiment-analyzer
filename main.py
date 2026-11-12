from legacy_db import init_db
from ingestion import fetch_all_feeds
from sentiment import CryptoSentimentEngine
from market_data import fetch_and_store_crypto_prices
from legacy_db import init_db, init_price_table, get_unscored_posts, update_sentiment_batch


def run_pipeline():
    print("========================================")
    print("🚀 RUNNING FULL END-TO-END PIPELINE")
    print("========================================")

    # 1. Initialize Tables
    init_db()
    init_price_table()

    # 2. Ingest RSS News & Reddit Feeds
    print("\n--- [Phase 1: Ingesting Social & News Data] ---")
    fetch_all_feeds()

    # 3. Sentiment Scoring
    print("\n--- [Phase 2: Computing NLP Sentiment Scores] ---")
    engine = CryptoSentimentEngine()
    unscored = get_unscored_posts()

    if unscored:
        updates = []
        for post_id, title, content in unscored:
            full_text = f"{title}. {content if content else ''}"
            score, label = engine.analyze_sentiment(full_text)
            updates.append((score, label, post_id))
        update_sentiment_batch(updates)
        print(f"✅ Processed and scored {len(updates)} posts.")
    else:
        print("⚡ All existing posts already scored.")

    # 4. Market Prices Ingestion
    print("\n--- [Phase 3: Ingesting Market Prices] ---")
    fetch_and_store_crypto_prices(period="7d", interval="1h")

    print("\n🎉 Pipeline executed successfully!")


if __name__ == "__main__":
    run_pipeline()