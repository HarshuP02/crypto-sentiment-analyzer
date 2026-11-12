# Real-Time Multi-Asset Crypto Sentiment & Quantitative Signal Engine

An autonomous, end-to-end intelligence pipeline that ingests real-time cryptocurrency news, extracts aspect-based market sentiment using a hybrid NLP architecture (FinBERT + VADER), detects quantitative price-sentiment divergences, and delivers automated high-conviction alerts via Discord and an interactive Streamlit terminal.

---

## Architecture Overview

```text
                  +-----------------------------+
                  |   Verified Open RSS Feeds   |
                  |  (CryptoPotato, Blockworks, |
                  |    CoinJournal, etc.)       |
                  +--------------+--------------+
                                 |
                                 v
                  +-----------------------------+
                  |    APScheduler Daemon       |
                  |  (15-min autonomous cycles) |
                  +--------------+--------------+
                                 |
                +----------------+----------------+
                v                                 v
  +---------------------------+     +---------------------------+
  |  NLP Sentiment Pipeline   |     |    Market Data Ingestion  |
  |  • Aspect Categorization  |     |  • Hourly Candles via     |
  |  • FinBERT (Contextual)   |     |    yfinance API           |
  |  • VADER (Lexical)        |     +-------------+-------------+
  +-------------+-------------+                   |
                |                                 |
                v                                 |
  +---------------------------+                   |
  |    PostgreSQL Database    |                   |
  |  (Persisted & Deduplicated|                   |
  |    via SHA-256 Hashes)    |                   |
  +-------------+-------------+                   |
                |                                 |
                +----------------+----------------+
                                 v
                  +-----------------------------+
                  | Divergence Detection Engine |
                  |  • 6-Hour Rolling Windows   |
                  |  • Price Slope vs Sent Slope|
                  +--------------+--------------+
                                 |
                +----------------+----------------+
                v                                 v
  +---------------------------+     +---------------------------+
  |    Discord Alert Engine   |     |    Streamlit Dashboard    |
  |  • Webhook Embed Cards    |     |  • Dual-Axis Plotly Charts|
  |  • State-Change Limiter   |     |  • Aspect Donuts & Feed   |
  +---------------------------+     +---------------------------+
```

---

## Key Features

* **Hybrid NLP Sentiment Pipeline**: Combines Hugging Face's `ProsusAI/finbert` for contextual financial sentiment and `VADER` for lexical intensity.
* **Aspect Categorization**: Classifies headlines and summaries across institutional crypto dimensions: *Regulation*, *Market*, and *Technology*.
* **Quantitative Divergence Detector**: Evaluates trailing 6-hour window price velocity against resampled hourly sentiment momentum to detect actionable leading signals (`BULLISH`, `BEARISH`, `NEUTRAL`).
* **Automated Webhook Dispatch with Anti-Spam**: Dispatches formatted embed cards to Discord on signal transitions, suppressing redundant notifications during sustained trends.
* **Multi-Asset Coverage**: Monitors 8 assets: Bitcoin (`BTC`), Ethereum (`ETH`), Solana (`SOL`), Chainlink (`LINK`), Cardano (`ADA`), Dogecoin (`DOGE`), Avalanche (`AVAX`), and Ripple (`XRP`).
* **Production-Ready Containerization**: Fully dockerized multi-container setup running PostgreSQL, an autonomous background ingestion daemon, and a Streamlit UI via Docker Compose.

---

## Tech Stack

| Layer | Technologies |
|---|---|
| **Core & Scheduling** | Python 3.11+, APScheduler, Pandas, NumPy |
| **NLP & Sentiment** | PyTorch, Hugging Face Transformers (`FinBERT`), NLTK / VADER |
| **Market Data & Feeds** | `yfinance`, Feedparser, Requests |
| **Database** | PostgreSQL 15, SQLAlchemy, Psycopg2 |
| **Alerting** | Discord Webhook API (JSON Embeds) |
| **Frontend & Analytics** | Streamlit, Plotly Graph Objects |
| **Infrastructure** | Docker, Docker Compose |

---

## Project Structure

```text
crypto-sentiment-analyzer/
├── alerts/
│   └── notifier.py              # Webhook delivery logic
├── config.py                    # Asset configurations & keywords
├── database/
│   ├── db_manager.py            # PostgreSQL schema & connection logic
│   └── models.py                # Database models
├── sentiment_engine.py          # Hybrid FinBERT + VADER pipeline
├── signals/
│   ├── divergence_detector.py   # Price-sentiment slope analysis
│   └── webhook_notifier.py      # Discord embed card formatting
├── app.py                       # Streamlit frontend application
├── scheduler_worker.py          # Autonomous background worker
├── docker-compose.yml           # Multi-container orchestration
├── Dockerfile                   # Python container configuration
├── requirements.txt             # Pinned project dependencies
└── README.md
```

---

## Getting Started

### 1. Prerequisites

* Docker Desktop installed and running
* A Discord channel Webhook URL

### 2. Environment Configuration

Create a `.env` file in the root directory:

```bash
# Database Configuration
DATABASE_URL=postgresql+psycopg2://crypto_user:crypto_password@postgres_db:5432/crypto_intelligence

# Alerting
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN
```

### 3. Build & Run via Docker Compose

Launch the PostgreSQL database, background ingestion daemon, and web dashboard:

```bash
docker compose up --build -d
```

Check container status:

```bash
docker compose ps
```

Monitor live ingestion and signal scanning:

```bash
docker compose logs -f background_worker
```

Access the interactive dashboard at [http://localhost:8501](http://localhost:8501).

---

## Local Development (Without Docker)

If you prefer to run services locally:

1. **Set up a virtual environment:**

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure your database:** Ensure PostgreSQL is running locally and update `DATABASE_URL` in `.env` (use `localhost` instead of `postgres_db` as the host).

3. **Start the background ingestion daemon:**

   ```bash
   python scheduler_worker.py
   ```

4. **Launch the Streamlit frontend:**

   ```bash
   streamlit run app.py
   ```

---

## Quantitative Signal Methodology

The engine calculates rolling divergence across a configurable window ($W = 6\text{ hours}$):

1. **Sentiment Velocity**: Aggregates and normalizes aspect-scored news into 1-hour intervals, computing the linear slope ($m_{\text{sentiment}}$) over the window.
2. **Price Velocity**: Pulls 1-hour candle close prices and computes the price trajectory slope ($m_{\text{price}}$).
3. **Signal Trigger**:
   * **Bullish Divergence**: $m_{\text{price}} \le 0$ while $m_{\text{sentiment}} > \tau$ (price stagnates/declines while institutional sentiment accelerates upward).
   * **Bearish Divergence**: $m_{\text{price}} \ge 0$ while $m_{\text{sentiment}} < -\tau$ (price climbs while narrative sentiment breaks down).

---

## License

This project is licensed under the MIT License.
