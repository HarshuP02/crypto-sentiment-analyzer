import sqlite3
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from market_data import get_merged_sentiment_price_data

# Page Configuration
st.set_page_config(
    page_title="Crypto Sentiment & Signal Engine",
    page_icon="⚡",
    layout="wide"
)

# Custom Styling
st.markdown("""
    <style>
    .metric-card {
        background-color: #1e2130;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.2);
    }
    </style>
""", unsafe_allow_html=True)

st.title("⚡ Real-Time Crypto Sentiment Analyzer & Signal Engine")
st.caption("Tracking multi-source social feeds, crypto news headlines, and price correlation.")

# Sidebar Filters & Controls
st.sidebar.header("🕹️ Dashboard Controls")
selected_coin = st.sidebar.selectbox("Select Asset", ["BTC", "ETH", "SOL"], index=0)

conn = sqlite3.connect("crypto_sentiment.db")

# Fetch General Stats for Selected Coin
stats_query = """
    SELECT 
        COUNT(*) as total_posts,
        AVG(sentiment_score) as avg_score,
        SUM(CASE WHEN sentiment_label = 'BULLISH' THEN 1 ELSE 0 END) as bullish_count,
        SUM(CASE WHEN sentiment_label = 'BEARISH' THEN 1 ELSE 0 END) as bearish_count,
        SUM(CASE WHEN sentiment_label = 'NEUTRAL' THEN 1 ELSE 0 END) as neutral_count
    FROM crypto_posts
    WHERE coin_tag = ?
"""
stats_df = pd.read_sql_query(stats_query, conn, params=(selected_coin,))

# Top KPI Metric Row
col1, col2, col3, col4 = st.columns(4)

total_mentions = stats_df['total_posts'].values[0] if not stats_df.empty else 0
avg_sentiment = stats_df['avg_score'].values[0] if not stats_df.empty and stats_df['avg_score'].values[0] is not None else 0.0
bullish_mentions = stats_df['bullish_count'].values[0] if not stats_df.empty else 0
bearish_mentions = stats_df['bearish_count'].values[0] if not stats_df.empty else 0

with col1:
    st.metric("Total Mentions Tracked", f"{total_mentions} posts")
with col2:
    sentiment_label = "🟢 Bullish" if avg_sentiment >= 0.15 else ("🔴 Bearish" if avg_sentiment <= -0.15 else "⚪ Neutral")
    st.metric("Overall Sentiment", f"{avg_sentiment:.3f}", sentiment_label)
with col3:
    st.metric("Bullish Signals", f"{bullish_mentions}")
with col4:
    st.metric("Bearish Signals", f"{bearish_mentions}")

st.divider()

# Dual-Axis Plot: Price vs Sentiment
st.subheader(f"📈 {selected_coin}/USD Price Action vs NLP Sentiment Polarity")
merged_data = get_merged_sentiment_price_data(selected_coin)

if not merged_data.empty:
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Price Line
    fig.add_trace(
        go.Scatter(
            x=merged_data['timestamp'],
            y=merged_data['close'],
            name=f"{selected_coin} Price (USD)",
            line=dict(color="#00FFA3", width=2.5)
        ),
        secondary_y=False
    )

    # Sentiment Bar Overlay
    colors = ['#00FFA3' if val > 0 else '#FF4B4B' for val in merged_data['avg_sentiment']]
    fig.add_trace(
        go.Bar(
            x=merged_data['timestamp'],
            y=merged_data['avg_sentiment'],
            name="Hourly Avg Sentiment",
            marker_color=colors,
            opacity=0.4
        ),
        secondary_y=True
    )

    fig.update_layout(
        template="plotly_dark",
        height=450,
        margin=dict(l=20, r=20, t=30, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    fig.update_yaxes(title_text="Price in USD ($)", secondary_y=False)
    fig.update_yaxes(title_text="Sentiment Score [-1.0 to 1.0]", secondary_y=True, range=[-1.1, 1.1])

    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("No price history available. Please run the backend pipeline to populate data.")

st.divider()

# Recent Social & News Feed Breakdown
st.subheader("📰 Live Ingested Feed Stream")
feed_query = """
    SELECT source, title, sentiment_score, sentiment_label, published_at
    FROM crypto_posts
    WHERE coin_tag = ? OR coin_tag = 'GENERAL'
    ORDER BY published_at DESC
    LIMIT 10
"""
feed_df = pd.read_sql_query(feed_query, conn, params=(selected_coin,))
conn.close()

if not feed_df.empty:
    for _, row in feed_df.iterrows():
        label_color = "green" if row['sentiment_label'] == 'BULLISH' else ("red" if row['sentiment_label'] == 'BEARISH' else "gray")
        with st.container():
            st.markdown(f"**[{row['source']}]** {row['title']}")
            st.markdown(
                f"Score: `{row['sentiment_score']}` | Status: :{label_color}[{row['sentiment_label']}] | Time: `{row['published_at']}`"
            )
            st.write("---")
else:
    st.info("No recent feeds detected for this asset.")