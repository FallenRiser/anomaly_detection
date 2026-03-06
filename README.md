# 🔗 Supply Chain Inventory Anomaly Explanation Assistant

An AI-powered assistant that explains inventory anomalies in Consumer Packaged Goods (CPG) supply chains. The system uses **LangChain** with **OpenAI GPT-4o** to investigate anomalies, identify root causes, and provide actionable recommendations.

## ✨ Features

- **AI-Powered Root Cause Analysis** — LangChain ReAct agent with Google Gemini investigates anomalies using SQL queries, knowledge base retrieval, and statistical analysis
- **Interactive Dashboard** — Real-time anomaly overview with Plotly charts
- **Anomaly Explorer** — Filterable, paginated anomaly list by type, severity, product, DC, and date
- **Detailed Investigation View** — Inventory history charts with anomaly markers + AI explanation panel
- **RAG Knowledge Base** — ChromaDB stores supply chain domain knowledge for context-aware explanations
- **CSV Upload** — Import custom inventory data for analysis
- **REST API** — JSON endpoints for programmatic access

## 🏗️ Architecture

```
User ──► Flask Web UI ──► LangChain ReAct Agent
                              │
                    ┌─────────┼─────────┐
                    ▼         ▼         ▼
              SQLite DB   ChromaDB   Statistical
             (inventory   (domain    Analysis
              records)   knowledge)  (trends)
                    │         │         │
                    └─────────┼─────────┘
                              ▼
                    Structured Explanation
                    (causes, evidence, actions)
```

## 📋 Tech Stack

| Component | Technology |
|-----------|------------|
| LLM | OpenAI GPT-4o (via LangChain) |
| Agent Framework | LangChain + LangGraph (ReAct agent) |
| Vector DB | ChromaDB (domain knowledge RAG) |
| Database | SQLite (inventory records) |
| Web Framework | Flask |
| Charts | Plotly.js |
| Frontend | HTML/CSS/JS (dark theme, glassmorphism) |

## 🚀 Setup & Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API Key

Edit the `.env` file and add your OpenAI API key:

```
OPENAI_API_KEY=your-actual-openai-api-key
```

You can get an API key from [OpenAI Platform](https://platform.openai.com/api-keys).

### 3. Generate Synthetic Data

```bash
python generate_data.py
```

This creates:
- `data/inventory_data.csv` — Raw CSV with ~36,500 records
- `data/inventory_data.db` — SQLite database with full schema

### 4. Initialize Knowledge Base

```bash
python knowledge_base.py
```

This populates ChromaDB with 16 supply chain domain knowledge documents.

### 5. Run the Application

```bash
python app.py
```

Open http://127.0.0.1:5000 in your browser.

## 📊 Input Data Format

### CSV Columns

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| `date` | YYYY-MM-DD | ✅ | Date of inventory record |
| `product_id` | String | ✅ | Product SKU identifier |
| `stock_level` | Integer | ✅ | Current stock quantity |
| `is_anomaly` | 0/1 | ✅ | Whether record is an anomaly |
| `product_name` | String | Optional | Product name |
| `category` | String | Optional | Product category |
| `distribution_center_id` | String | Optional | DC identifier |
| `sales_rate` | Float | Optional | Daily sales rate |
| `demand_forecast` | Float | Optional | Predicted demand |
| `anomaly_type` | String | Optional | stockout / overstock / demand_spike / supply_delay / shrinkage / forecast_error |
| `anomaly_severity` | String | Optional | critical / high / medium |

### Anomaly Types

| Type | Description |
|------|-------------|
| `stockout` | Stock at or near zero, unable to fulfill demand |
| `overstock` | Excess inventory well above normal levels |
| `demand_spike` | Sudden surge in sales rate exceeding forecasts |
| `supply_delay` | Lead time significantly longer than expected |
| `shrinkage` | Unexplained inventory loss (theft, damage, spoilage) |
| `forecast_error` | Significant deviation between forecast and actual demand |

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/anomalies` | List anomalies (supports query params: type, severity, product, dc, date_from, date_to) |
| `GET` | `/api/stats` | Dashboard statistics |
| `GET` | `/api/anomaly/<id>/history` | Anomaly context with surrounding inventory history |
| `POST` | `/explain` | Generate AI explanation (body: `{"anomaly_id": 1}`) |

## 🧠 How the AI Agent Works

The agent follows a structured investigation process:

1. **Data Gathering** — Queries SQLite for the anomaly record and 14 days of surrounding inventory history
2. **Trend Analysis** — Computes z-scores, moving averages, and trend direction
3. **Knowledge Retrieval** — Searches ChromaDB for relevant root cause patterns and resolution playbooks
4. **Synthesis** — Combines evidence to produce a structured explanation with:
   - Root causes ranked by likelihood
   - Supporting data evidence
   - Impact assessment
   - Recommended actions (immediate, short-term, long-term)
   - Confidence level

## 📁 Project Structure

```
anomaly detection/
├── app.py                  # Flask web application
├── agent.py                # LangChain anomaly explanation agent
├── config.py               # Centralized configuration
├── database.py             # SQLite query helpers
├── generate_data.py        # Synthetic data generator
├── knowledge_base.py       # ChromaDB knowledge base
├── requirements.txt        # Python dependencies
├── .env                    # API key configuration
├── README.md               # This file
├── data/                   # Generated data (auto-created)
│   ├── inventory_data.db
│   ├── inventory_data.csv
│   └── chroma_db/
├── templates/              # HTML templates
│   ├── base.html
│   ├── dashboard.html
│   ├── anomalies.html
│   ├── anomaly_detail.html
│   └── upload.html
└── static/                 # CSS & JS
    ├── style.css
    └── app.js
```

