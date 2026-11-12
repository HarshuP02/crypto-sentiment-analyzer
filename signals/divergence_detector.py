import numpy as np
import pandas as pd


class DivergenceDetector:
    def __init__(self, window: int = 6, sent_threshold: float = 0.15):
        self.window = window
        self.sent_threshold = sent_threshold

    def scan_divergence(self, df: pd.DataFrame) -> dict:
        if df.empty or len(df) < self.window:
            return {
                "signal": "NEUTRAL",
                "latest_price": 0.0,
                "price_slope": 0.0,
                "sentiment_slope": 0.0,
                "latest_sentiment": 0.0,
                "reason": "Insufficient aligned hourly bars.",
            }

        recent = df.tail(self.window)
        x = np.arange(len(recent), dtype=float)

        closes = recent["close"].astype(float).to_numpy()
        sentiments = recent["sentiment_score"].astype(float).to_numpy()
        latest_price = round(float(closes[-1]), 4)

        # Normalize price slope (% change per hour) so thresholds work across BTC and DOGE
        mean_price = float(np.mean(closes))
        raw_price_slope = float(np.polyfit(x, closes, 1)[0])
        price_slope = (raw_price_slope / mean_price) if mean_price > 0 else 0.0

        sent_slope = float(np.polyfit(x, sentiments, 1)[0])
        latest_sent = float(sentiments[-1])

        # Guard: if sentiment is flat across the window, no divergence exists
        if np.isclose(sent_slope, 0.0, atol=1e-6):
            return {
                "signal": "NEUTRAL",
                "latest_price": latest_price,
                "price_slope": round(price_slope, 6),
                "sentiment_slope": 0.0,
                "latest_sentiment": round(latest_sent, 4),
                "reason": "Sentiment slope is flat across the lookback window.",
            }

        signal = "NEUTRAL"
        reason = "Price and sentiment are aligned or trendless."

        # Bullish Divergence: Price falling/flat (<= 0) while sentiment trends upward (> 0)
        if price_slope <= 0 and sent_slope > 0.02 and latest_sent >= self.sent_threshold:
            signal = "BULLISH"
            reason = "Bullish divergence: price declining/flat while sentiment momentum turns positive."

        # Bearish Divergence: Price rising/flat (>= 0) while sentiment trends downward (< 0)
        elif price_slope >= 0 and sent_slope < -0.02 and latest_sent <= -self.sent_threshold:
            signal = "BEARISH"
            reason = "Bearish divergence: price rising/flat while sentiment momentum turns negative."

        return {
            "signal": signal,
            "latest_price": latest_price,
            "price_slope": round(price_slope, 6),
            "sentiment_slope": round(sent_slope, 4),
            "latest_sentiment": round(latest_sent, 4),
            "reason": reason,
        }