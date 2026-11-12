# config.py
from dotenv import load_dotenv
import os
from pathlib import Path

# Explicitly locate .env in the project root directory
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

RAW_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://crypto_user:crypto_password@localhost:5432/crypto_intelligence"
)


# Auto-detect whether running inside Docker or directly on host (PyCharm/local terminal)
def get_resolved_db_url(url: str) -> str:
    # If .dockerenv exists or DOCKER_CONTAINER env is set, we are in a container
    is_in_docker = os.path.exists("/.dockerenv") or os.getenv("IS_DOCKER", "false").lower() == "true"

    if not is_in_docker and "@postgres_db:" in url:
        # Running directly in PyCharm / Local host -> swap container hostname to localhost
        return url.replace("@postgres_db:", "@localhost:")
    return url


DATABASE_URL = get_resolved_db_url(RAW_DATABASE_URL)
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")

SUPPORTED_ASSETS = {
    "BTC": {
        "name": "Bitcoin",
        "yf_ticker": "BTC-USD",
        "keywords": ["btc", "bitcoin", "satoshi nakamoto"]
    },
    "ETH": {
        "name": "Ethereum",
        "yf_ticker": "ETH-USD",
        "keywords": ["eth", "ethereum", "vitalik", "vitalik buterin", "ether"]
    },
    "SOL": {
        "name": "Solana",
        "yf_ticker": "SOL-USD",
        "keywords": ["solana", "anatoly yakovenko"]
    },
    "XRP": {
        "name": "XRP",
        "yf_ticker": "XRP-USD",
        "keywords": ["xrp", "ripple", "brad garlinghouse", "garlinghouse"]
    },
    "ADA": {
        "name": "Cardano",
        "yf_ticker": "ADA-USD",
        "keywords": ["cardano", "charles hoskinson", "hoskinson"]
    },
    "DOGE": {
        "name": "Dogecoin",
        "yf_ticker": "DOGE-USD",
        "keywords": ["doge", "dogecoin"]
    },
    "AVAX": {
        "name": "Avalanche",
        "yf_ticker": "AVAX-USD",
        "keywords": ["avax", "avalanche"]
    },
    "LINK": {
        "name": "Chainlink",
        "yf_ticker": "LINK-USD",
        "keywords": ["chainlink", "sergey nazarov"]
    }
}