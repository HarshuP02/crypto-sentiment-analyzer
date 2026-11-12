from sentiment_engine import HybridSentimentEngine

def run_test():
    engine = HybridSentimentEngine()

    sample_inputs = [
        ("SEC delays approval on spot ETF applications amid regulatory uncertainty.", "news"),
        ("Ethereum gas fees drop to 6-month lows following network upgrade and layer 2 adoption.", "news"),
        ("Bitcoin surges past resistance as massive whale liquidations ignite a short squeeze!", "reddit"),
        ("Solana network suffers 4-hour validator outage after smart contract bug.", "news")
    ]

    print("\n" + "=" * 75)
    for text, source in sample_inputs:
        result = engine.analyze_item(text, source_type=source)
        print(f"Text: \"{result['text']}\"")
        print(f"  • Source:    {result['source'].upper()}")
        print(f"  • Aspects:   {', '.join(result['aspects'])}")
        print(f"  • Model:     {result['sentiment']['engine'].upper()}")
        print(f"  • Sentiment: {result['sentiment']['label']} (Score: {result['sentiment']['score']:+.4f})")
        print("-" * 75)

if __name__ == "__main__":
    run_test()