import re
import ssl
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer

# Fix macOS Python SSL certificate verification for downloading NLTK datasets
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

# Download VADER lexicon
try:
    nltk.data.find('sentiment/vader_lexicon.zip')
except LookupError:
    nltk.download('vader_lexicon', quiet=True)

# Custom crypto-specific sentiment weights
CRYPTO_LEXICON_OVERRIDES = {
    "bullish": 3.0,
    "moon": 2.5,
    "mooning": 2.8,
    "pump": 2.0,
    "ath": 2.5,
    "breakout": 2.0,
    "hodl": 1.5,
    "accumulate": 1.8,
    "bearish": -3.0,
    "dump": -2.8,
    "dumping": -3.0,
    "rekt": -3.5,
    "rug": -3.5,
    "rugpull": -4.0,
    "fud": -2.0,
    "crash": -3.0,
    "liquidation": -2.5,
    "scam": -3.5
}


class CryptoSentimentEngine:
    def __init__(self):
        self.analyzer = SentimentIntensityAnalyzer()
        self.analyzer.lexicon.update(CRYPTO_LEXICON_OVERRIDES)

    def clean_text(self, text: str) -> str:
        """Removes URLs, markdown formatting, and non-ASCII artifacts."""
        if not text:
            return ""
        text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
        text = re.sub(r'[\r\n]+', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def analyze_sentiment(self, text: str):
        """Returns compound score (-1.0 to 1.0) and sentiment label."""
        cleaned = self.clean_text(text)
        if not cleaned:
            return 0.0, "NEUTRAL"

        scores = self.analyzer.polarity_scores(cleaned)
        compound = scores['compound']

        if compound >= 0.15:
            label = "BULLISH"
        elif compound <= -0.15:
            label = "BEARISH"
        else:
            label = "NEUTRAL"

        return round(compound, 4), label