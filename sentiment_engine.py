import os
import re
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from models.finbert_analyzer import FinBERTAnalyzer
from models.aspect_extractor import AspectExtractor

# 1. Auto-download VADER lexicon if missing
try:
    nltk.data.find("sentiment/vader_lexicon.zip")
except LookupError:
    nltk.download("vader_lexicon", quiet=True)

# 2. Configure local cache directory so FinBERT persists across container restarts
CACHE_DIR = os.getenv("HF_HOME", os.path.expanduser("~/.cache/huggingface"))
os.environ.setdefault("HF_HOME", CACHE_DIR)

LABEL_MAP = {
    "positive": "BULLISH",
    "bullish": "BULLISH",
    "negative": "BEARISH",
    "bearish": "BEARISH",
    "neutral": "NEUTRAL",
}


def normalize_label(raw_label: str) -> str:
    """Unifies FinBERT and VADER output labels to BULLISH, BEARISH, or NEUTRAL."""
    return LABEL_MAP.get(raw_label.lower().strip(), "NEUTRAL")


class HybridSentimentEngine:
    def __init__(self, custom_slang: dict | None = None):
        # 1. Initialize VADER with expanded crypto trading lexicon
        self.vader = SentimentIntensityAnalyzer()
        # noinspection SpellCheckingInspection
        crypto_lexicon = {
            # Slang
            "moon": 3.0, "pumping": 2.5, "pump": 2.5, "bullish": 3.0,
            "rekt": -3.5, "dump": -3.0, "dumping": -3.0, "rugpull": -3.8,
            "diamond hands": 2.8, "paper hands": -2.5,

            # Trading terminology missing from standard VADER
            "surge": 2.5, "surges": 2.5, "surging": 2.5,
            "rally": 2.2, "rallies": 2.2, "rallying": 2.2,
            "breakout": 2.0, "short squeeze": 2.8,
            "outage": -3.0, "exploit": -3.5, "hack": -3.5,
            "liquidation": -1.5, "liquidations": -1.5,
        }

        if custom_slang:
            crypto_lexicon.update(custom_slang)

        self.vader.lexicon.update(crypto_lexicon)

        # 2. Lazy-load FinBERT (single instance) and Aspect Extractor
        self.finbert: FinBERTAnalyzer | None = None
        self.aspect_extractor = AspectExtractor()

    def _init_finbert(self) -> FinBERTAnalyzer:
        if self.finbert is None:
            self.finbert = FinBERTAnalyzer()
        return self.finbert

    @staticmethod
    def _has(text: str, terms: list[str]) -> bool:
        """Checks if any term appears as a whole word (bounded by \\b) in text."""
        return any(re.search(r"\b" + re.escape(t) + r"\b", text) for t in terms)

    def _adjust_crypto_domain_context(self, text: str, score_data: dict) -> dict:
        """
        Fixes domain-inversion using whole-word matching so words like
        'following' do not falsely match 'low'.
        """
        cleaned = text.lower()
        fee_terms = ["gas fee", "gas fees", "transaction fee", "transaction fees", "gwei"]
        drop_terms = ["drop", "drops", "dropped", "low", "lows", "cheaper", "reduction", "plummet"]

        has_fee = self._has(cleaned, fee_terms)
        has_drop = self._has(cleaned, drop_terms)

        if has_fee and has_drop and score_data["score"] < 0:
            inverted_score = abs(score_data["score"]) * 0.8
            score_data["score"] = round(inverted_score, 4)
            score_data["label"] = "BULLISH"
            score_data["adjusted_reason"] = "Crypto domain inversion: Lower network fees = positive adoption."

        return score_data

    def analyze_item(self, text: str, source_type: str = "news") -> dict:
        aspects = self.aspect_extractor.extract_aspects(text)

        if source_type.strip().lower() == "reddit":
            vader_res = self.vader.polarity_scores(text)
            compound = float(vader_res["compound"])
            label = "BULLISH" if compound >= 0.05 else ("BEARISH" if compound <= -0.05 else "NEUTRAL")
            score_data = {
                "engine": "vader",
                "label": label,
                "score": compound,
                "details": vader_res,
            }
        else:
            finbert = self._init_finbert()
            finbert_res = finbert.predict(text)
            score_data = {
                "engine": "finbert",
                "label": normalize_label(str(finbert_res["label"])),
                "score": float(finbert_res["score"]),
                "details": finbert_res["probabilities"],
            }

        # Apply crypto domain adjustments
        score_data = self._adjust_crypto_domain_context(text, score_data)

        # Guarantee unified label vocabulary across all engines
        score_data["label"] = LABEL_MAP.get(
            str(score_data["label"]).strip().lower(),
            "NEUTRAL"
        )

        return {
            "text": text,
            "source": source_type,
            "aspects": aspects,
            "sentiment": score_data,
        }