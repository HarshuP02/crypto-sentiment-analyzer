import re
import hashlib
import feedparser
from datetime import datetime
from legacy_db import insert_post

COIN_KEYWORDS = {
    "BTC": ["bitcoin", "btc", "sats"],
    "ETH": ["ethereum", "eth", "vitalik"],
    "SOL": ["solana", "sol"]
}

# Major Crypto News Feeds + Reddit RSS Feeds (No API keys or auth needed)
FEEDS = {
    "CoinDesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "CoinTelegraph": "https://cointelegraph.com/rss",
    "Decrypt": "https://decrypt.co/feed",
    "Reddit_rCryptoCurrency": "https://www.reddit.com/r/CryptoCurrency/.rss",
    "Reddit_rBitcoin": "https://www.reddit.com/r/Bitcoin/.rss",
    "Reddit_rSolana": "https://www.reddit.com/r/solana/.rss"
}

def detect_coin_tag(text: str) -> str:
    t = text.lower()
    for tag, kws in COIN_KEYWORDS.items():
        if any(re.search(r"\b" + re.escape(k) + r"\b", t) for k in kws):
            return tag
    return "GENERAL"


def fetch_all_feeds():
    """Fetches and stores posts from all news and Reddit RSS endpoints."""
    print("📡 Ingesting live feeds from Crypto News & Reddit...")

    # Custom User-Agent to avoid Reddit blocks
    user_agent = "CryptoSentimentTrackerBot/1.0"

    for source_name, url in FEEDS.items():
        try:
            feed = feedparser.parse(url, agent=user_agent)
            entries = feed.entries[:15]  # Process latest 15 entries per feed

            for entry in entries:
                title = entry.get("title", "")
                summary = entry.get("summary", "")
                full_text = f"{title} {summary}"

                link = entry.get("link", title)
                post_id = hashlib.md5(link.encode('utf-8')).hexdigest()
                coin_tag = detect_coin_tag(full_text)
                published_at = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

                insert_post(
                    post_id=post_id,
                    source=source_name,
                    title=title,
                    content=summary,
                    published_at=published_at,
                    coin_tag=coin_tag
                )
            print(f" -> Successfully fetched {len(entries)} items from {source_name}")
        except Exception as e:
            print(f"❌ Failed to fetch from {source_name}: {e}")