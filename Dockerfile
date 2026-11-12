FROM python:3.11-slim

# Prevent Python from writing .pyc files, enable unbuffered logging, and set HF cache path
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV HF_HOME=/root/.cache/huggingface
RUN mkdir -p /root/.cache/huggingface

WORKDIR /app

# Install system build dependencies required for compiling drivers
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download VADER lexicon & FinBERT weights at build time to prevent cold-start latency
RUN python -c "import nltk; nltk.download('vader_lexicon')"
RUN python -c "from transformers import AutoTokenizer, AutoModelForSequenceClassification; AutoTokenizer.from_pretrained('ProsusAI/finbert'); AutoModelForSequenceClassification.from_pretrained('ProsusAI/finbert')"

# Copy application code
COPY . .

# Expose Streamlit's default port
EXPOSE 8501

# Default health check for Streamlit
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1