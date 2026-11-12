import os
import streamlit as st

# Streamlit page config MUST be called before any other Streamlit command
st.set_page_config(
    page_title="Multi-Asset Crypto Sentiment & Signal Engine",
    page_icon="⚡",
    layout="wide"
)

from datetime import datetime, timedelta, timezone
import pandas as pd
import plotly.graph_objects as go
import yfinance as yf
from config import SUPPORTED_ASSETS  # Loads .env automatically at import
from database.db_manager import DatabaseManager
from signals.divergence_detector import DivergenceDetector

# Only run worker in Streamlit if explicitly enabled (defaults to "0" / disabled)
if os.getenv("RUN_BACKGROUND_WORKER", "0") == "1":
    from scheduler_worker import start_background_worker

    @st.cache_resource
    def init_worker():
        return start_background_worker()

    _ = init_worker()

# Initialize database adapter and divergence detector
db = DatabaseManager()
detector = DivergenceDetector(window=6)

st.title("⚡ Multi-Asset Crypto Sentiment & Signal Engine")
st.caption("Real-Time Aspect-Based NLP (FinBERT + VADER) & Market Divergence Detection")

# Top controls
col_ctrl1, col_ctrl2, col_ctrl3 = st.columns([3, 2, 2])
asset_options = list(SUPPORTED_ASSETS.keys())
format_func = lambda t: f"{t} — {SUPPORTED_ASSETS[t]['name']}"

with col_ctrl1:
    selected_ticker = st.selectbox("Select Asset", asset_options, format_func=format_func, index=0)
with col_ctrl2:
    timeframe = st.selectbox("Look-Back Window", ["24 Hours", "48 Hours", "7 Days"], index=1)
with col_ctrl3:
    if st.button("🔄 Refresh Data", width="stretch"):
        st.rerun()

days_map = {"24 Hours": "1d", "48 Hours": "2d", "7 Days": "7d"}
hours = {"24 Hours": 24, "48 Hours": 48, "7 Days": 168}[timeframe]
since = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")

# 1. Fetch asset-specific posts matching the exact lookback window
raw_posts = db.get_recent_posts(ticker=selected_ticker, since=since)
posts_df: pd.DataFrame = raw_posts if isinstance(raw_posts, pd.DataFrame) else pd.DataFrame()

# 2. Fetch market candles via yfinance safely
yf_ticker = SUPPORTED_ASSETS[selected_ticker]["yf_ticker"]
try:
    downloaded_data = yf.download(
        tickers=yf_ticker,
        period=days_map[timeframe],
        interval="1h",
        progress=False,
        multi_level_index=False
    )
    price_df: pd.DataFrame = downloaded_data if isinstance(downloaded_data, pd.DataFrame) else pd.DataFrame()
except Exception as e:
    price_df = pd.DataFrame()
    st.error(f"Error loading price data for {yf_ticker}: {e}")

# 3. Top Metric Cards & Signals
st.markdown("---")

# A. Calculate Base Sentiment & Volume
if not posts_df.empty and "score" in posts_df.columns:
    score_col = pd.Series(pd.to_numeric(posts_df["score"], errors="coerce"))
    avg_score: float = float(score_col.mean()) if not score_col.dropna().empty else 0.0
    total_posts: int = int(len(posts_df))
else:
    avg_score = 0.0
    total_posts = 0

# B. Calculate Price & Price Change safely with explicit Series wrapping
latest_price: float = 0.0
price_change: float = 0.0

if not price_df.empty and "Close" in price_df.columns and len(price_df) > 0:
    close_series = pd.Series(pd.to_numeric(price_df["Close"], errors="coerce")).dropna()
    if len(close_series) > 0:
        latest_val = float(close_series.iloc[-1])
        first_val = float(close_series.iloc[0])
        latest_price = latest_val
        if len(close_series) > 1 and first_val != 0.0:
            price_change = float(((latest_val - first_val) / first_val) * 100)

# C. Calculate Engine Signal (strictly aligned to price candle hours)
sig: str = "NEUTRAL"
if not price_df.empty and not posts_df.empty and len(price_df) >= 6 and "Close" in price_df.columns:
    valid_price = price_df.dropna(subset=["Close"])
    if len(valid_price) >= 6:
        price_hours = pd.to_datetime(valid_price.index, utc=True).tz_localize(None).floor("h")
        sent_ts = pd.to_datetime(posts_df["published_at"], utc=True).dt.tz_localize(None)

        sent_series = pd.Series(
            pd.to_numeric(posts_df["score"], errors="coerce").to_numpy(),
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
        div_result = detector.scan_divergence(div_df)
        sig = str(div_result.get("signal", "NEUTRAL")).upper()

# D. Render Columns using the synchronized 'sig'
metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)

with metric_col1:
    st.metric(f"{selected_ticker} Price", f"${latest_price:,.2f}", f"{price_change:+.2f}%")

with metric_col2:
    st.markdown("**Sentiment Score**")
    st.markdown(
        f"<div style='font-size: 1.8rem; font-weight: 700; margin-top: -6px; margin-bottom: 6px;'>{avg_score:+.4f}</div>",
        unsafe_allow_html=True
    )

    if "BULLISH" in sig:
        st.markdown(
            '<span style="background-color:rgba(0,255,128,0.15); border: 1.2px solid #00FF80; '
            'color:#00FF80; font-size:0.85rem; font-weight:700; padding:3px 10px; border-radius:6px; display:inline-block;">'
            '🟢 BULLISH</span>',
            unsafe_allow_html=True
        )
    elif "BEARISH" in sig:
        st.markdown(
            '<span style="background-color:rgba(255,68,68,0.15); border: 1.2px solid #FF4444; '
            'color:#FF4444; font-size:0.85rem; font-weight:700; padding:3px 10px; border-radius:6px; display:inline-block;">'
            '🔴 BEARISH</span>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            '<span style="background-color:rgba(180,180,180,0.15); border: 1.2px solid #888888; '
            'color:#888888; font-size:0.85rem; font-weight:600; padding:3px 10px; border-radius:6px; display:inline-block;">'
            '⚪ NEUTRAL</span>',
            unsafe_allow_html=True
        )

with metric_col3:
    st.metric("Tracked Mentions", total_posts)

with metric_col4:
    st.markdown("**Engine Signal**")
    if "BULLISH" in sig:
        st.markdown(
            '<div style="background-color:rgba(0,255,128,0.15);border:1.5px solid #00FF80;border-radius:8px;padding:6px 14px;display:inline-block;">'
            '<span style="color:#00FF80;font-size:1.2rem;font-weight:700;letter-spacing:0.5px;">🟢 BULLISH</span>'
            '</div>',
            unsafe_allow_html=True
        )
    elif "BEARISH" in sig:
        st.markdown(
            '<div style="background-color:rgba(255,68,68,0.15);border:1.5px solid #FF4444;border-radius:8px;padding:6px 14px;display:inline-block;">'
            '<span style="color:#FF4444;font-size:1.2rem;font-weight:700;letter-spacing:0.5px;">🔴 BEARISH</span>'
            '</div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            '<div style="background-color:rgba(180,180,180,0.12);border:1.5px solid #888888;border-radius:8px;padding:6px 14px;display:inline-block;">'
            '<span style="color:#BBBBBB;font-size:1.2rem;font-weight:600;">⚪ NEUTRAL</span>'
            '</div>',
            unsafe_allow_html=True
        )

# 4. Interactive Dual-Axis Plotly Chart
st.markdown(f"### 📈 {selected_ticker} Price vs. Sentiment Trajectory")

if not price_df.empty and "Close" in price_df.columns:
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=price_df.index,
        y=price_df["Close"],
        name=f"{selected_ticker} Price (USD)",
        line=dict(color="#00FFAA", width=2),
        yaxis="y1"
    ))

    if not posts_df.empty and "score" in posts_df.columns:
        posts_plot_df = posts_df.copy()
        posts_plot_df["timestamp_dt"] = pd.to_datetime(posts_plot_df["published_at"])
        posts_plot_df["score"] = pd.Series(pd.to_numeric(posts_plot_df["score"], errors="coerce"))
        hourly_agg = pd.Series(
            posts_plot_df.set_index("timestamp_dt")["score"]
            .resample("1h")
            .mean()
        ).dropna()

        fig.add_trace(go.Scatter(
            x=hourly_agg.index,
            y=hourly_agg.values,
            name="Aggregated Sentiment",
            mode="lines+markers",
            line=dict(color="#FF9900", width=2, dash="dot"),
            yaxis="y2"
        ))

    fig.update_layout(
        template="plotly_dark",
        height=420,
        margin=dict(l=10, r=10, t=40, b=40),
        xaxis=dict(title="Time"),
        yaxis=dict(title=f"Price ({selected_ticker} USD)", side="left"),
        yaxis2=dict(
            title="Sentiment Score (-1.0 to +1.0)",
            overlaying="y",
            side="right",
            range=[-1.05, 1.05]
        ),
        legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5)
    )

    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
else:
    st.info(f"No price data available for {selected_ticker}.")

# 5. ABSA & Scored Feed Breakdown
col_aspect, col_posts = st.columns([1, 2])

with col_aspect:
    st.markdown("### 🏷️ Aspect Breakdown")
    if not posts_df.empty and "aspect" in posts_df.columns:
        aspect_counts = posts_df["aspect"].value_counts().reset_index()
        aspect_counts.columns = ["Aspect", "Count"]

        pie_fig = go.Figure(data=[go.Pie(
            labels=aspect_counts["Aspect"],
            values=aspect_counts["Count"],
            hole=0.45
        )])
        pie_fig.update_layout(
            template="plotly_dark",
            height=320,
            margin=dict(l=10, r=10, t=10, b=40),
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
        )
        st.plotly_chart(pie_fig, width="stretch", config={"displayModeBar": False})
    else:
        st.caption(f"No aspect records tagged for {selected_ticker} yet.")

with col_posts:
    st.markdown(f"### 📰 Recent {selected_ticker} Scored Feed")
    if not posts_df.empty:
        required_cols = ["published_at", "source", "aspect", "label", "score", "title"]
        present_cols = [c for c in required_cols if c in posts_df.columns]
        display_df = posts_df[present_cols].copy()
        if "score" in display_df.columns:
            display_score = pd.Series(pd.to_numeric(display_df["score"], errors="coerce"))
            display_df["score"] = display_score.map(lambda x: f"{x:+.3f}")
        st.dataframe(display_df, width="stretch", height=280)
    else:
        st.caption(f"No recent news or posts tagged for {selected_ticker}.")