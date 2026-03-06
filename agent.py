"""
LangChain Anomaly Explanation Agent.

Uses OpenAI GPT-4o LLM with tools for SQL queries, knowledge base search,
and statistical analysis to generate root-cause explanations for inventory anomalies.
"""
import json
import statistics
from datetime import datetime
from typing import Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

import config
import database
import knowledge_base


# ── Tools ──────────────────────────────────────────────────────────────────

@tool
def query_inventory_database(sql_query: str) -> str:
    """Run a read-only SQL query against the inventory database to fetch data.

    Available tables:
    - inventory_records (record_id, date, product_id, product_name, category,
      distribution_center_id, distribution_center, region, stock_level,
      reorder_point, sales_rate, demand_forecast, lead_time_days, supplier,
      is_anomaly, anomaly_type, anomaly_severity)
    - products (product_id, product_name, category, supplier, base_stock,
      base_sales_rate, shelf_life_days)
    - distribution_centers (dc_id, dc_name, region, capacity)
    - anomaly_log (anomaly_id, record_id, date, product_id,
      distribution_center_id, anomaly_type, anomaly_severity, explanation)

    Only SELECT queries are allowed. Always LIMIT results to avoid huge outputs.
    """
    try:
        results = database.run_custom_query(sql_query)
        if not results:
            return "Query returned no results."
        # Limit output size
        output = json.dumps(results[:50], indent=2, default=str)
        return f"Query returned {len(results)} rows (showing up to 50):\n{output}"
    except Exception as e:
        return f"Query error: {str(e)}"


@tool
def search_supply_chain_knowledge(query: str) -> str:
    """Search the supply chain domain knowledge base for relevant information.

    Use this to find root cause patterns, resolution playbooks, seasonal patterns,
    best practices, and investigation guidelines relevant to the anomaly being analyzed.

    Args:
        query: Natural language description of what you're looking for.
    """
    try:
        results = knowledge_base.search_knowledge(query, top_k=4)
        if not results:
            return "No relevant knowledge found."
        output = ""
        for i, r in enumerate(results, 1):
            output += f"\n--- Knowledge #{i} [{r['metadata']['topic']}/{r['metadata']['type']}] ---\n"
            output += r["content"] + "\n"
        return output
    except Exception as e:
        return f"Knowledge search error: {str(e)}"


@tool
def analyze_inventory_trend(
    product_id: str,
    distribution_center_id: str,
    anomaly_date: str,
    days_before: int = 14,
    days_after: int = 7,
) -> str:
    """Analyze statistical trends around an anomaly date for a product at a DC.

    Computes moving averages, standard deviations, z-scores, and identifies
    trend patterns in stock levels and sales rates.

    Args:
        product_id: Product SKU ID (e.g., 'SKU001')
        distribution_center_id: Distribution center ID (e.g., 'DC01')
        anomaly_date: The date of the anomaly (YYYY-MM-DD)
        days_before: Days of history to analyze before anomaly (default 14)
        days_after: Days to analyze after anomaly (default 7)
    """
    try:
        history = database.get_product_history(
            product_id, distribution_center_id, anomaly_date, days_before, days_after
        )
        if not history:
            return "No historical data found for the specified parameters."

        stocks = [r["stock_level"] for r in history]
        sales = [r["sales_rate"] for r in history]
        dates = [r["date"] for r in history]

        # Find anomaly date index
        anomaly_idx = None
        for i, d in enumerate(dates):
            if d == anomaly_date:
                anomaly_idx = i
                break

        # Basic statistics
        stock_mean = statistics.mean(stocks) if stocks else 0
        stock_stdev = statistics.stdev(stocks) if len(stocks) > 1 else 0
        sales_mean = statistics.mean(sales) if sales else 0
        sales_stdev = statistics.stdev(sales) if len(sales) > 1 else 0

        # Z-score of anomaly point
        anomaly_stock = stocks[anomaly_idx] if anomaly_idx is not None else None
        anomaly_sales = sales[anomaly_idx] if anomaly_idx is not None else None

        stock_zscore = ((anomaly_stock - stock_mean) / stock_stdev) if stock_stdev and anomaly_stock is not None else None
        sales_zscore = ((anomaly_sales - sales_mean) / sales_stdev) if sales_stdev and anomaly_sales is not None else None

        # Trend detection (pre-anomaly)
        pre_stocks = stocks[:anomaly_idx] if anomaly_idx else stocks[:len(stocks)//2]
        if len(pre_stocks) >= 3:
            first_half = statistics.mean(pre_stocks[:len(pre_stocks)//2])
            second_half = statistics.mean(pre_stocks[len(pre_stocks)//2:])
            stock_trend = "declining" if second_half < first_half * 0.9 else (
                "increasing" if second_half > first_half * 1.1 else "stable"
            )
        else:
            stock_trend = "insufficient data"

        # Moving average (5-day)
        ma_5 = []
        for i in range(len(stocks)):
            window = stocks[max(0, i-4):i+1]
            ma_5.append(round(statistics.mean(window), 1))

        # Forecast accuracy
        forecasts = [r["demand_forecast"] for r in history]
        forecast_errors = [abs(s - f) / max(s, 1) * 100 for s, f in zip(sales, forecasts)]
        avg_forecast_error = round(statistics.mean(forecast_errors), 1) if forecast_errors else None

        analysis = {
            "period": f"{dates[0]} to {dates[-1]}",
            "data_points": len(history),
            "stock_level": {
                "mean": round(stock_mean, 1),
                "std_dev": round(stock_stdev, 1),
                "min": min(stocks),
                "max": max(stocks),
                "anomaly_value": anomaly_stock,
                "z_score": round(stock_zscore, 2) if stock_zscore is not None else None,
                "pre_anomaly_trend": stock_trend,
            },
            "sales_rate": {
                "mean": round(sales_mean, 1),
                "std_dev": round(sales_stdev, 1),
                "min": min(sales),
                "max": max(sales),
                "anomaly_value": anomaly_sales,
                "z_score": round(sales_zscore, 2) if sales_zscore is not None else None,
            },
            "forecast_accuracy": {
                "avg_error_pct": avg_forecast_error,
            },
            "moving_average_5d": dict(zip(dates[-5:], ma_5[-5:])),
            "daily_data": [
                {"date": d, "stock": s, "sales": sl, "forecast": f}
                for d, s, sl, f in zip(dates, stocks, sales, forecasts)
            ],
        }

        return json.dumps(analysis, indent=2, default=str)
    except Exception as e:
        return f"Analysis error: {str(e)}"


# ── Agent System Prompt ────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert Supply Chain Analyst AI specializing in Consumer Packaged Goods (CPG) inventory anomaly investigation. Your role is to analyze inventory anomalies and provide clear, actionable root-cause explanations.

## Your Investigation Process:
1. **Gather Data** — Use the SQL query tool to fetch the anomaly record and its surrounding data (14 days before, 7 days after). Check the product's baseline metrics and the DC's typical patterns.
2. **Analyze Trends** — Use the trend analysis tool to compute statistical measures (z-scores, moving averages, trend direction) for context.
3. **Consult Knowledge Base** — Search the supply chain knowledge base for known root cause patterns and resolution playbooks matching the anomaly type.
4. **Synthesize Explanation** — Combine data evidence with domain knowledge to produce a structured, professional explanation.

## Output Format:
Your explanation MUST follow this structure:

### 📋 Anomaly Summary
Brief description of the anomaly (what, where, when, severity).

### 🔍 Root Cause Analysis
List probable causes ranked by likelihood, each with supporting evidence from the data.

### 📊 Data Evidence
Key statistical findings that support your analysis (z-scores, trends, deviations from normal).

### ⚠️ Impact Assessment
Estimated business impact — service level risk, revenue impact, working capital implications.

### ✅ Recommended Actions
Concrete, actionable steps divided into:
- **Immediate** (next 24-48 hours)
- **Short-term** (next 1-2 weeks)
- **Long-term** (systemic improvements)

### 📈 Confidence Level
Your confidence in the analysis: HIGH / MEDIUM / LOW with brief justification.

## Guidelines:
- Always use actual data from the database to support your claims
- Be specific — cite numbers, dates, and percentages
- Consider seasonal patterns, regional factors, and product category norms
- If multiple causes are possible, present them ranked by probability
- Make recommendations proportional to the severity of the anomaly
- Think like a senior supply chain analyst presenting to management
"""


# ── Agent Creation ─────────────────────────────────────────────────────────

def create_explanation_agent():
    """Create the LangChain anomaly explanation agent."""
    llm = ChatOpenAI(
        model=config.LLM_MODEL,
        openai_api_key=config.OPENAI_API_KEY,
        temperature=config.LLM_TEMPERATURE,
        http_client=config.CUSTOM_HTTP_CLIENT,
    )

    tools = [
        query_inventory_database,
        search_supply_chain_knowledge,
        analyze_inventory_trend,
    ]

    agent = create_react_agent(
        model=llm,
        tools=tools,
    )

    return agent


def explain_anomaly(anomaly_id: int) -> dict:
    """Generate an AI explanation for a specific anomaly.

    Args:
        anomaly_id: The anomaly_log ID to explain.

    Returns:
        dict with keys: explanation, probable_causes, recommended_actions, confidence
    """
    # Fetch the anomaly context
    context = database.get_context_for_anomaly(anomaly_id)
    if not context or not context.get("anomaly"):
        return {"error": f"Anomaly {anomaly_id} not found."}

    anomaly = context["anomaly"]
    product = context["product"]
    dc = context["distribution_center"]

    # Build the prompt
    user_message = f"""Investigate and explain the following inventory anomaly:

**Anomaly Details:**
- Anomaly ID: {anomaly.get('anomaly_id')}
- Date: {anomaly['date']}
- Product: {anomaly['product_name']} ({anomaly['product_id']})
- Category: {anomaly['category']}
- Distribution Center: {anomaly['distribution_center']} ({anomaly['distribution_center_id']})
- Region: {anomaly['region']}
- Anomaly Type: {anomaly['anomaly_type']}
- Severity: {anomaly['anomaly_severity']}

**Current Metrics:**
- Stock Level: {anomaly['stock_level']} units
- Reorder Point: {anomaly['reorder_point']} units
- Sales Rate: {anomaly['sales_rate']} units/day
- Demand Forecast: {anomaly['demand_forecast']} units/day
- Lead Time: {anomaly['lead_time_days']} days
- Supplier: {anomaly['supplier']}

**Product Baseline:**
- Normal Base Stock: {product['base_stock']} units
- Normal Sales Rate: {product['base_sales_rate']} units/day
- Shelf Life: {product['shelf_life_days']} days

**Distribution Center:**
- DC: {dc['dc_name']} ({dc['region']} region)
- Capacity: {dc['capacity']} units

Please conduct a thorough investigation using the available tools and provide a comprehensive explanation."""

    # Run the agent
    agent = create_explanation_agent()
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_message),
    ]

    result = agent.invoke({"messages": messages})

    # Extract the final response
    final_message = result["messages"][-1].content

    # Save to database
    database.save_explanation(
        anomaly_id=anomaly_id,
        explanation=final_message,
        causes=anomaly["anomaly_type"],
        actions="See explanation for details",
        confidence=0.85,
    )

    return {
        "anomaly_id": anomaly_id,
        "explanation": final_message,
        "anomaly_type": anomaly["anomaly_type"],
        "severity": anomaly["anomaly_severity"],
        "product": anomaly["product_name"],
        "dc": anomaly["distribution_center"],
        "date": anomaly["date"],
    }


# ── Batch Explanation ──────────────────────────────────────────────────────

def explain_multiple(anomaly_ids: list[int]) -> list[dict]:
    """Explain multiple anomalies."""
    results = []
    for aid in anomaly_ids:
        try:
            result = explain_anomaly(aid)
            results.append(result)
        except Exception as e:
            results.append({"anomaly_id": aid, "error": str(e)})
    return results


if __name__ == "__main__":
    # Test with the first anomaly
    import sys
    anomaly_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    print(f"🔄 Explaining anomaly #{anomaly_id}...")
    result = explain_anomaly(anomaly_id)
    if "error" in result:
        print(f"❌ Error: {result['error']}")
    else:
        print(f"\n{'='*80}")
        print(f"Anomaly: {result['anomaly_type']} | {result['product']} @ {result['dc']}")
        print(f"Date: {result['date']} | Severity: {result['severity']}")
        print(f"{'='*80}")
        print(result["explanation"])
