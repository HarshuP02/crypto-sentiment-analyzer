import pandas as pd
from signals.divergence_detector import DivergenceDetector


def run_test():
    detector = DivergenceDetector(window=6)

    # Simulated 6-hour window: Price is dropping, but sentiment is aggressively climbing
    mock_data = {
        "timestamp": pd.date_range(end=pd.Timestamp.now(), periods=6, freq="1h"),
        "close": [64500.0, 64200.0, 63900.0, 63600.0, 63200.0, 62900.0],  # Downtrend
        "sentiment_score": [-0.10, -0.05, 0.10, 0.22, 0.35, 0.48],        # Climbing sentiment
    }
    df = pd.DataFrame(mock_data)

    result = detector.scan_divergence(df)

    print("\n" + "=" * 65)
    print("DIVERGENCE ENGINE TEST OUTPUT:")
    print(f"  • Signal:          {result['signal']}")
    print(f"  • Latest Price:    ${result['latest_price']:,.2f}")
    print(f"  • Latest Score:    {result['latest_sentiment']:+.4f}")
    print(f"  • Price Slope:     {result['price_slope']:+.6f}")
    print(f"  • Sentiment Slope: {result['sentiment_slope']:+.4f}")
    print(f"  • Reason:          {result['reason']}")
    print("=" * 65)


if __name__ == "__main__":
    run_test()