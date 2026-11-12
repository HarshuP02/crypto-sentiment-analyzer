import re

class AspectExtractor:
    def __init__(self):
        # Curated keyword dictionaries for each crypto market aspect
        self.aspect_lexicon = {
            "REGULATORY": [
                "sec", "cftc", "etf", "regulation", "regulatory", "lawsuit", "court",
                "judge", "compliance", "ban", "legal", "subpoena", "gensler", "fed",
                "interest rate", "treasury", "policy", "sanction", "approval", "delay"
            ],
            "ON_CHAIN_TECH": [
                "fork", "upgrade", "node", "hashrate", "gas fee", "network", "validator",
                "exploit", "hack", "bug", "smart contract", "bridge", "outage", "downtime",
                "layer 2", "rollup", "staking", "mainnet", "testnet", "protocol"
            ],
            "MARKET_PRICE": [
                "ath", "all-time high", "all time high", "pump", "dump", "bull", "bear",
                "liquidation", "short squeeze", "long", "short", "rally", "crash",
                "dip", "breakout", "resistance", "support", "volume", "market cap",
                "whale", "accumulation", "rekt", "moon"
            ]
        }

    def extract_aspects(self, text: str) -> list[str]:
        """
        Scans text and returns all matching aspect categories.
        Defaults to ['GENERAL'] if no specific domain keywords are matched.
        """
        if not text:
            return ["GENERAL"]

        cleaned = text.lower()
        matched_aspects = []

        for aspect, keywords in self.aspect_lexicon.items():
            for kw in keywords:
                # Use regex word boundaries so 'ban' doesn't trigger inside 'bank'
                pattern = r'\b' + re.escape(kw) + r'\b'
                if re.search(pattern, cleaned):
                    matched_aspects.append(aspect)
                    break

        return matched_aspects if matched_aspects else ["GENERAL"]