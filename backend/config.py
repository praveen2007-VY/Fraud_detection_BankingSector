import os
from pathlib import Path
from typing import List

# Resolve project root and .env path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"

if ENV_PATH.exists():
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

# Environment settings
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "fraud_detection_2026")

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
KAFKA_INPUT_TOPIC = os.getenv("KAFKA_INPUT_TOPIC", "transactions")
KAFKA_PROCESSED_TOPIC = os.getenv("KAFKA_PROCESSED_TOPIC", "processed_transactions")

RAW_CORS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000")
CORS_ORIGINS: List[str] = [origin.strip() for origin in RAW_CORS.split(",") if origin.strip()]

RISK_SCORE_THRESHOLD = float(os.getenv("RISK_SCORE_THRESHOLD", "50.0"))
ANOMALY_SCORE_THRESHOLD = float(os.getenv("ANOMALY_SCORE_THRESHOLD", "0.5"))

DATA_DIR = PROJECT_ROOT / "data"
NEO4J_DIR = PROJECT_ROOT / "neo4j"
ML_DIR = PROJECT_ROOT / "ml"

CLEAN_TRANSACTIONS_CSV = DATA_DIR / "transactions_clean.csv"
SCORED_TRANSACTIONS_CSV = NEO4J_DIR / "scored_transactions.csv"
C2GAT_SCORES_CSV = ML_DIR / "c2gat_scores.csv"
C2GAT_MODEL_PT = ML_DIR / "c2gat_model.pt"
C2GAT_SCALER_PKL = ML_DIR / "c2gat_scaler.pkl"
