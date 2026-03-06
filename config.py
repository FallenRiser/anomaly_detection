"""
Centralized configuration for the Supply Chain Anomaly Explanation Assistant.
"""
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

# ── SSL Bypass HTTP Client ─────────────────────────────────────────────────
CUSTOM_HTTP_CLIENT = httpx.Client(verify=False)

# ── LLM Configuration ──────────────────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
LLM_MODEL = "gpt-4o"
EMBEDDING_MODEL = "text-embedding-3-small"
LLM_TEMPERATURE = 0.3

# ── Database Paths ──────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SQLITE_DB_PATH = os.path.join(BASE_DIR, "data", "inventory_data.db")
CHROMA_PERSIST_DIR = os.path.join(BASE_DIR, "data", "chroma_db")
CSV_OUTPUT_PATH = os.path.join(BASE_DIR, "data", "inventory_data.csv")

# ── Data Generation ────────────────────────────────────────────────────────
NUM_PRODUCTS = 20
NUM_DISTRIBUTION_CENTERS = 5
DATA_START_DATE = "2025-03-01"
DATA_END_DATE = "2026-02-28"
ANOMALY_RATE = 0.15  # ~15% of records will be anomalies

# ── ChromaDB ───────────────────────────────────────────────────────────────
CHROMA_COLLECTION_NAME = "supply_chain_knowledge"
RAG_TOP_K = 5

# ── Flask ──────────────────────────────────────────────────────────────────
FLASK_HOST = "127.0.0.1"
FLASK_PORT = 5000
FLASK_DEBUG = True
