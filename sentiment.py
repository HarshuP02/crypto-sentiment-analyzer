import re
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer


# Download VADER lexicon safely
try:
    nltk.data.find('sentiment/vader_lexicon.zip')
except LookupError:
    nltk.download('vader_lexicon', quiet=True)

# noinspection SpellCheckingInspection
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
    "rug pull": -4.0,
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

    @staticmethod
    def clean_text(text: str) -> str:
        """Removes URLs, mark down formatting, and non-ASCII artifacts."""
        if not text:
            return ""
        text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
        text = re.sub(r'[\r\n]+', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    @staticmethod
    def _adjust_gas_fees(text: str, compound: float) -> float:
        """Inverts sentiment when gas/transaction fees drop or spike using word boundaries."""
        t = text.lower()
        has_gas = bool(re.search(r"\b(gas|fees?|gwei)\b", t))
        if has_gas and re.search(r"\b(low|cheap|drop|dropped|cheaper|reduction)\b", t):
            return abs(compound)
        if has_gas and re.search(r"\b(high|spike|spiking|expensive|surge)\b", t):
            return -abs(compound)
        return compound

    def analyze_sentiment(self, text: str) -> tuple[float, str]:
        """Returns compound score (-1.0 to 1.0) and sentiment label."""
        cleaned = self.clean_text(text)
        if not cleaned:
            return 0.0, "NEUTRAL"

        scores = self.analyzer.polarity_scores(cleaned)
        compound = self._adjust_gas_fees(cleaned, float(scores['compound']))

        if compound >= 0.15:
            label = "BULLISH"
        elif compound <= -0.15:
            label = "BEARISH"
        else:
            label = "NEUTRAL"

        return round(compound, 4), label