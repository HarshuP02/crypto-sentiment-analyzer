import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification


class FinBERTAnalyzer:
    def __init__(self, model_name: str = "ProsusAI/finbert"):
        """
        Initializes FinBERT tokenizer and pre-trained model.
        Runs inference on GPU if available, else falls back to CPU.
        """
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name).to(self.device)
        self.model.eval()

        # Read label mapping directly from the loaded model's Hugging Face config
        self.labels = [
            self.model.config.id2label[i].lower()
            for i in range(len(self.model.config.id2label))
        ]

    def predict(self, text: str) -> dict:
        """
        Predicts sentiment label, probabilities, and a normalized compound score [-1.0 to 1.0].
        """
        if not text or not text.strip():
            return {
                "label": "neutral",
                "score": 0.0,
                "probabilities": {"positive": 0.0, "negative": 0.0, "neutral": 1.0},
            }

        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=128,
        ).to(self.device)

        with torch.no_grad():
            outputs = self.model(**inputs)
            probs = torch.nn.functional.softmax(outputs.logits, dim=-1).squeeze().tolist()

        prob_dict = {
            label: float(prob) for label, prob in zip(self.labels, probs)
        }

        # Determine dominant label
        max_idx = probs.index(max(probs))
        predicted_label = self.labels[max_idx]

        # Map to continuous polarity: P(positive) - P(negative) [-1.0 to +1.0]
        compound_score = prob_dict.get("positive", 0.0) - prob_dict.get("negative", 0.0)

        return {
            "label": predicted_label.upper(),
            "score": round(compound_score, 4),
            "probabilities": {k: round(v, 4) for k, v in prob_dict.items()},
        }