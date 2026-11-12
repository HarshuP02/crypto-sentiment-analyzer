import os
import json
import requests


class WebhookNotifier:
    def __init__(
            self,
            discord_url: str = None
    ):
        # Read from direct arguments or default to environment variables
        self.discord_url = discord_url or os.getenv("DISCORD_WEBHOOK_URL")

    def send_discord(self, asset: str, alert_data: dict) -> bool:
        """Sends an embed notification card to a Discord channel."""
        if not self.discord_url:
            return False

        sig = alert_data.get("signal", "NEUTRAL").upper()

        # Color mapping matched to standardized engine signals
        color_map = {
            "BULLISH": 0x00FF80,  # Emerald Green
            "BEARISH": 0xFF4444,  # Crimson Red
            "NEUTRAL": 0x888888   # Gray
        }
        color = color_map.get(sig, 0x888888)
        emoji = "🟢" if "BULLISH" in sig else ("🔴" if "BEARISH" in sig else "⚪")
        description = alert_data.get("reason") or alert_data.get("description", "No description provided.")

        payload = {
            "username": "Crypto Signal Engine",
            "embeds": [{
                "title": f"{emoji} {sig} Alert — {asset}",
                "description": description,
                "color": color,
                "fields": [
                    {"name": "Current Price", "value": f"${alert_data.get('latest_price', 0.0):,.2f}", "inline": True},
                    {"name": "Sentiment Score", "value": f"{alert_data.get('latest_sentiment', 0.0):+.4f}",
                     "inline": True},
                    {"name": "Sentiment Slope", "value": f"{alert_data.get('sentiment_slope', 0.0):+.4f}/hr",
                     "inline": True}
                ],
                "footer": {"text": "Crypto Sentiment & Divergence Engine • Automated Alert"}
            }]
        }

        try:
            res = requests.post(
                self.discord_url,
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"},
                timeout=5
            )
            return res.status_code in [200, 204]
        except Exception as e:
            print(f"[WebhookNotifier] Discord send failed: {e}")
            return False

    def broadcast(self, asset: str, alert_data: dict):
        """Sends alerts across all configured channels only for actionable signals."""
        sig = alert_data.get("signal", "NEUTRAL").upper()
        if sig in ["BULLISH", "BEARISH"]:
            if self.discord_url:
                self.send_discord(asset, alert_data)