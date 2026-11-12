import re
import hashlib
import threading
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import requests
import feedparser
import yfinance as yf
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.blocking import BlockingScheduler
from dotenv import load_dotenv
from config import SUPPORTED_ASSETS
from database.db_manager import DatabaseManager
from sentiment_engine import HybridSentimentEngine
from signals.divergence_detector import DivergenceDetector
from signals.webhook_notifier import WebhookNotifier

load_dotenv(override=False)

# Initialize managers and detectors at module level
db = DatabaseManager()
engine = HybridSentimentEngine()
detector = DivergenceDetector(window=6)
notifier = WebhookNotifier()

# Anti-Spam Rate Limiter: Tracks the last emitted signal per asset
LAST_ALERTED_STATE = {}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/rss+xml, application/xml, text/xml, */*"
}

OPEN_FEEDS = {
    "CryptoPotato": "https://cryptopotato.com/feed/",
    "CoinJournal": "https://coinjournal.net/news/feed/",
    "CoinJournal_Altcoins": "https://coinjournal.net/news/tag/altcoins/feed/",
    "Blockworks": "https://blockworks.co/feed"
}


def fetch_live_articles() -> list[dict]:
    items = []
    for source_name, url in OPEN_FEEDS.items():
        try:
            res = requests.get(url, headers=HEADERS, timeout=8)
            if res.status_code != 200:
                continue
            feed = feedparser.parse(res.content)
            for entry in feed.entries:
                title = getattr(entry, "title", "")
                summary = getattr(entry, "summary", "")
                if title:
                    lower_src = source_name.lower()
                    item_type = "reddit" if ("reddit" in lower_src or lower_src.startswith("r/")) else "news"
                    items.append({
                        "title": title,
                        "content": f"{title} {summary}",
                        "source": source_name,
                        "type": item_type
                    })
        except Exception as e:
            print(f"  • [Feed Warning] {source_name}: {e}")
    return items


def match_tickers(text: str) -> list[str]:
    cleaned = text.lower()
    matched = set()
    for ticker, details in SUPPORTED_ASSETS.items():
        for kw in details["keywords"]:
            if re.search(r'\b' + re.escape(kw.lower()) + r'\b', cleaned):
                matched.add(ticker)
                break
    return list(matched)


def scheduled_job():
    """Runs the full ingestion, scoring, divergence evaluation, and alert cycle."""
    now_utc = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n[{now_utc}] ⏳ Fetching verified open crypto feeds...")

    articles = fetch_live_articles()
    print(f"  • Retrieved {len(articles)} raw articles from open feeds.")

    asset_counts = {t: 0 for t in SUPPORTED_ASSETS.keys()}
    total_saved = 0

    # 1. Ingest, score, and persist raw news items
    for item in articles:
        title = item["title"]
        content = item["content"]
        source = item["source"]
        src_type = item["type"]

        tickers = match_tickers(content)
        if not tickers:
            continue

        analysis = engine.analyze_item(title, source_type=src_type)
        aspect = analysis["aspects"][0]
        score = analysis["sentiment"]["score"]
        label = analysis["sentiment"]["label"]

        for ticker in tickers:
            post_hash = hashlib.sha256(f"{ticker}_{title.strip().lower()}".encode("utf-8")).hexdigest()
            db.insert_post(
                post_hash=post_hash,
                source=source,
                ticker=ticker,
                title=title,
                aspect=aspect,
                score=score,
                label=label,
                published_at=now_utc
            )
            asset_counts[ticker] += 1
            total_saved += 1

    print(f"  • Scored items stored per asset: {asset_counts}")
    print(f"✅ Total records saved this cycle: {total_saved}")

    # 2. Per-Asset Market Divergence Scanning & Alert Dispatch
    print("📡 Scanning market divergence & triggering alerts...")
    for ticker, details in SUPPORTED_ASSETS.items():
        try:
            recent_posts = db.get_recent_posts(ticker=ticker, limit=100)
            if recent_posts.empty:
                continue

            yf_ticker = details["yf_ticker"]
            price_data = yf.download(
                tickers=yf_ticker,
                period="2d",
                interval="1h",
                progress=False,
                multi_level_index=False
            )

            if not price_data.empty and len(price_data) >= 6 and "Close" in price_data.columns:
                valid_price = price_data.dropna(subset=["Close"])
                if len(valid_price) < 6:
                    continue

                # Align sentiment timestamps onto exact tz-naive UTC price candle hours
                price_hours = pd.to_datetime(valid_price.index, utc=True).tz_localize(None).floor("h")
                sent_ts = pd.to_datetime(recent_posts["published_at"], utc=True).dt.tz_localize(None)

                sent_series = pd.Series(
                    pd.to_numeric(recent_posts["score"], errors="coerce").to_numpy(),
                    index=sent_ts
                ).dropna().sort_index()

                hourly_sent = (
                    sent_series.resample("1h")
                    .mean()
                    .reindex(price_hours)
                    .ffill()
                    .fillna(0.0)
                )

                div_df = pd.DataFrame({
                    "close": pd.to_numeric(valid_price["Close"], errors="coerce").tail(6).to_numpy(dtype=float),
                    "sentiment_score": hourly_sent.tail(6).to_numpy(dtype=float),
                })

                result = detector.scan_divergence(div_df)
                sig = str(result.get("signal", "NEUTRAL")).upper()

                # --- RATE-LIMITED ALERT DISPATCH ---
                if sig in ["BULLISH", "BEARISH"]:
                    if LAST_ALERTED_STATE.get(ticker) != sig:
                        notifier.broadcast(asset=ticker, alert_data=result)
                        LAST_ALERTED_STATE[ticker] = sig
                        print(f"  • [Alert Dispatched] {ticker} transitioned to {sig}")
                    else:
                        print(f"  • [Alert Suppressed] {ticker} remains {sig} (anti-spam active)")
                elif sig == "NEUTRAL":
                    LAST_ALERTED_STATE[ticker] = "NEUTRAL"

        except Exception as e:
            print(f"  • [Signal/Alert Warning] {ticker}: {e}")

    print("🏁 Ingestion and alert cycle finished.")
    Path("/tmp/worker_heartbeat").touch()


def start_background_worker():
    """
    Initializes a background daemon scheduler that runs scheduled_job every 15 minutes.
    Defined AFTER scheduled_job so Python finds the reference.
    """
    scheduler = BackgroundScheduler(timezone=timezone.utc, daemon=True)
    scheduler.add_job(
        scheduled_job,
        trigger='interval',
        minutes=15,
        id='crypto_sentiment_ingestor',
        replace_existing=True
    )
    scheduler.start()
    print("🚀 Background scheduler started (polling every 15 mins).")

    first_run_thread = threading.Thread(target=scheduled_job, daemon=True)
    first_run_thread.start()

    return scheduler


if __name__ == "__main__":
    blocking_sched = BlockingScheduler()
    blocking_sched.add_job(
        scheduled_job,
        'interval',
        minutes=15,
        next_run_time=datetime.now(timezone.utc)
    )
    print("🚀 Standalone scheduler active. Press Ctrl+C to terminate.")
    try:
        blocking_sched.start()
    except (KeyboardInterrupt, SystemExit):
        pass