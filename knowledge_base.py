"""
ChromaDB Knowledge Base for Supply Chain Domain Knowledge.

Embeds CPG supply chain best practices, root cause patterns, and resolution
playbooks into a vector database for RAG-based retrieval.
"""
import os

import chromadb

import config


# ── Supply Chain Domain Knowledge ──────────────────────────────────────────

KNOWLEDGE_DOCUMENTS = [
    # ── Stockout Root Causes ───────────────────────────────────────────
    {
        "content": (
            "STOCKOUT ROOT CAUSES: Common causes of inventory stockouts in CPG include: "
            "1) Demand forecast underestimation — actual demand exceeds prediction due to "
            "unplanned promotions, viral trends, or competitor stockouts driving customers. "
            "2) Supplier delivery failures — supplier capacity issues, raw material shortages, "
            "or logistics disruptions. 3) Reorder point misconfiguration — safety stock too low "
            "for product velocity. 4) Warehouse processing delays — receiving dock bottlenecks "
            "or labor shortages. 5) Seasonal demand surge without pre-positioning inventory. "
            "6) Distribution network disruptions from weather, strikes, or transportation issues."
        ),
        "metadata": {"topic": "stockout", "type": "root_cause"},
    },
    {
        "content": (
            "STOCKOUT RESOLUTION PLAYBOOK: When stockout is detected: "
            "1) IMMEDIATE — Check alternate DCs for stock transfer. Contact supplier for "
            "emergency shipment. Activate backup supplier if primary cannot fulfill. "
            "2) SHORT-TERM — Adjust reorder points upward by 20-30%. Increase safety stock. "
            "Set up automated alerts for when stock falls below 1.5x reorder point. "
            "3) LONG-TERM — Implement demand sensing with POS data. Diversify supplier base. "
            "Add safety stock buffers proportional to demand variability. Review and optimize "
            "replenishment frequency."
        ),
        "metadata": {"topic": "stockout", "type": "resolution"},
    },
    # ── Overstock / Surplus ────────────────────────────────────────────
    {
        "content": (
            "OVERSTOCK ROOT CAUSES: Excess inventory in CPG typically results from: "
            "1) Demand forecast overestimation — predicted demand higher than actual, often "
            "after promotional events end or seasonal transitions. 2) Duplicate ordering — "
            "system errors or manual order placement when automated orders already dispatched. "
            "3) Cancelled promotions — inventory pre-positioned for promotions that were "
            "cancelled or postponed. 4) Customer returns or order cancellations. "
            "5) Product lifecycle end — new version launching while old stock remains. "
            "6) Batch size constraints — minimum order quantities exceeding actual need."
        ),
        "metadata": {"topic": "overstock", "type": "root_cause"},
    },
    {
        "content": (
            "OVERSTOCK RESOLUTION PLAYBOOK: When overstock is detected: "
            "1) IMMEDIATE — Halt incoming orders for the SKU. Check for expiration risk "
            "especially for perishable goods. 2) SHORT-TERM — Initiate clearance/markdown "
            "pricing. Transfer excess to DCs with higher sell-through. Coordinate with "
            "marketing for promotion push. 3) LONG-TERM — Reduce MOQ in supplier contracts. "
            "Implement demand-driven replenishment (pull vs push). Use AI/ML for more "
            "accurate demand forecasting. Monitor days-of-supply metrics daily."
        ),
        "metadata": {"topic": "overstock", "type": "resolution"},
    },
    # ── Demand Spike ──────────────────────────────────────────────────
    {
        "content": (
            "DEMAND SPIKE ROOT CAUSES: Sudden demand surges in CPG arise from: "
            "1) Promotional events — BOGO offers, festival sales, flash deals driving "
            "2-5x normal demand. 2) Viral social media trends — influencer endorsements "
            "or viral product reviews. 3) Competitor stockout — customers switching brands. "
            "4) Seasonal events — Diwali, Holi, monsoon season, summer heat waves for beverages. "
            "5) Panic buying — pandemic fears, weather events, supply shortage rumors. "
            "6) New distribution channel activation — e-commerce launch, new retail partnerships."
        ),
        "metadata": {"topic": "demand_spike", "type": "root_cause"},
    },
    {
        "content": (
            "DEMAND SPIKE RESPONSE: When demand spike is identified: "
            "1) Determine cause — check for active promotions, competitor activity, or external "
            "events. 2) Accelerate replenishment — expedite supplier orders, consider air freight. "
            "3) Activate safety stock allocation across DCs based on regional demand. "
            "4) If sustainable increase, update forecast models with new demand pattern. "
            "5) If temporary, plan for post-spike demand drop to avoid overstock."
        ),
        "metadata": {"topic": "demand_spike", "type": "resolution"},
    },
    # ── Supply Delay ──────────────────────────────────────────────────
    {
        "content": (
            "SUPPLY DELAY ROOT CAUSES: Supply chain delays in CPG occur due to: "
            "1) Supplier production issues — equipment breakdown, quality failures, raw material "
            "shortages. 2) Transportation disruptions — port congestion, truck driver shortages, "
            "route closures from weather or construction. 3) Customs/regulatory delays — "
            "documentation issues, inspection backlogs for imported goods. "
            "4) Warehouse receiving constraints — dock scheduling conflicts, labor shortages. "
            "5) Information delays — purchase order errors, EDI system failures. "
            "6) Force majeure — natural disasters, political instability, pandemics."
        ),
        "metadata": {"topic": "supply_delay", "type": "root_cause"},
    },
    {
        "content": (
            "SUPPLY DELAY MITIGATION: When supply delay is identified: "
            "1) Contact supplier for revised ETA and root cause. "
            "2) Identify substitute products or alternate suppliers. "
            "3) Redistribute existing inventory from low-demand to high-demand DCs. "
            "4) Communicate delays to downstream customers/retailers with revised timelines. "
            "5) For recurring delays, negotiate penalty clauses and build buffer lead times. "
            "6) Consider nearshoring or multi-sourcing strategies for critical SKUs."
        ),
        "metadata": {"topic": "supply_delay", "type": "resolution"},
    },
    # ── Shrinkage ─────────────────────────────────────────────────────
    {
        "content": (
            "SHRINKAGE ROOT CAUSES: Inventory shrinkage in CPG occurs due to: "
            "1) Theft — internal employee theft or external pilferage during transit. "
            "2) Damage — mishandling during loading/unloading, poor storage conditions, "
            "temperature excursions for sensitive goods. 3) Spoilage — expiration of "
            "perishable goods, pest contamination. 4) Administrative errors — miscounts, "
            "incorrect scanning, system sync failures between WMS and ERP. "
            "5) Vendor fraud — short shipments billed as complete. "
            "6) Process waste — breakage during repacking or display setup."
        ),
        "metadata": {"topic": "shrinkage", "type": "root_cause"},
    },
    {
        "content": (
            "SHRINKAGE PREVENTION: To address inventory shrinkage: "
            "1) Implement cycle counting programs with ABC analysis. "
            "2) Install CCTV and access controls in warehouse zones. "
            "3) Use RFID/barcode scanning at every handoff point. "
            "4) Implement FIFO/FEFO for perishable goods. "
            "5) Conduct receiving audits — count and verify against PO and bill of lading. "
            "6) Investigate patterns — if shrinkage is concentrated in specific shifts, "
            "locations, or product types, focus security measures. "
            "7) Use AI anomaly detection to flag unusual inventory adjustments."
        ),
        "metadata": {"topic": "shrinkage", "type": "resolution"},
    },
    # ── Forecast Error ────────────────────────────────────────────────
    {
        "content": (
            "FORECAST ERROR ROOT CAUSES: Significant forecast errors in CPG stem from: "
            "1) Model limitations — statistical models not capturing non-linear demand "
            "patterns, new product launches with no history. 2) Data quality issues — "
            "incorrect POS data, missing promotional lift factors, outdated seasonality curves. "
            "3) External shocks — unexpected competitor actions, regulatory changes, "
            "macroeconomic shifts. 4) Promotional misalignment — forecast not updated when "
            "promotions are added, changed, or cancelled. 5) Channel mix shifts — growing "
            "e-commerce channel not reflected in forecasts calibrated on brick-and-mortar data. "
            "6) New product cannibalization effects not modeled."
        ),
        "metadata": {"topic": "forecast_error", "type": "root_cause"},
    },
    {
        "content": (
            "FORECAST IMPROVEMENT: To reduce forecast errors: "
            "1) Incorporate real-time POS data and demand sensing signals. "
            "2) Use ensemble methods combining statistical and ML models. "
            "3) Implement collaborative forecasting with key retail partners. "
            "4) Add promotional lift factors and markdown effects to models. "
            "5) Monitor forecast accuracy (MAPE, bias) by SKU-location weekly. "
            "6) Conduct monthly S&OP reviews comparing forecast vs actual. "
            "7) Use causal AI to identify leading indicators of demand changes."
        ),
        "metadata": {"topic": "forecast_error", "type": "resolution"},
    },
    # ── Seasonal Patterns ─────────────────────────────────────────────
    {
        "content": (
            "SEASONAL PATTERNS IN CPG INDIA: Key seasonal demand patterns include: "
            "1) SUMMER (April-June): Beverages +40-60%, ice cream +80%, sunscreen +50%. "
            "Personal care and hygiene products increase. AC and fan filters spike. "
            "2) MONSOON (July-September): Umbrella and rain gear peak. Hot beverages increase. "
            "Snack consumption rises (indoor activity). Healthcare/cold medicine increases. "
            "3) FESTIVAL SEASON (October-December): Diwali drives confectionery +50%, "
            "dry fruits +100%, home care +20%. Christmas/New Year drives beverages. "
            "4) WINTER (January-March): Skincare/moisturizer +30%. Hot beverages +25%. "
            "Dairy demand stable. Cleaning products pre-Holi spike in February-March."
        ),
        "metadata": {"topic": "seasonal", "type": "pattern"},
    },
    # ── Supply Chain Best Practices ───────────────────────────────────
    {
        "content": (
            "CPG INVENTORY MANAGEMENT BEST PRACTICES: "
            "1) Safety Stock Formula: SS = Z × σ_LT × √LT where Z is service level factor, "
            "σ_LT is demand std dev, LT is lead time. For critical SKUs, use 95% service level. "
            "2) Reorder Point: ROP = (Average Daily Demand × Lead Time) + Safety Stock. "
            "3) ABC-XYZ Classification: A-items (80% revenue) get highest attention. "
            "X-items (stable demand) use automated replenishment. "
            "4) Days of Supply target: Perishables 3-7 days, FMCG 14-21 days, "
            "Durable goods 30-60 days. "
            "5) Perfect Order Rate target: >95% (right product, quantity, time, condition). "
            "6) Inventory Turnover benchmark: Grocery 14-20x/year, Personal care 8-12x/year."
        ),
        "metadata": {"topic": "best_practices", "type": "knowledge"},
    },
    {
        "content": (
            "ANOMALY INVESTIGATION CHECKLIST FOR ANALYSTS: "
            "When investigating an inventory anomaly, follow this structured approach: "
            "1) WHAT — Identify the specific metrics that deviate (stock level, sales rate, "
            "lead time, forecast accuracy). Quantify the deviation from normal. "
            "2) WHEN — Determine exact timing. Is it a point anomaly or persistent trend? "
            "Check preceding 14 days for early warning signals. "
            "3) WHERE — Is it isolated to one DC or affecting multiple locations? "
            "Check if upstream supply or downstream demand is affected. "
            "4) WHY — Cross-reference with promotions calendar, supplier communications, "
            "weather events, and competitor activity. "
            "5) IMPACT — Estimate revenue impact, customer service level impact, "
            "and working capital implications. "
            "6) ACTION — Define immediate containment, short-term fix, and long-term prevention."
        ),
        "metadata": {"topic": "investigation", "type": "process"},
    },
    {
        "content": (
            "DISTRIBUTION CENTER OPERATIONS AND ANOMALY PATTERNS: "
            "Common DC-level anomaly patterns include: "
            "1) Receiving bottlenecks — If multiple large shipments arrive simultaneously, "
            "putaway delays can cause phantom stockouts (stock exists but not available). "
            "2) Cross-dock failures — Items intended for immediate transfer stuck in staging. "
            "3) Pick accuracy — Wrong items picked leading to ghost inventory. "
            "4) Capacity constraints — During peak seasons, DCs may operate above capacity "
            "leading to put-away delays, increased damage rates, and shipping errors. "
            "5) System latency — WMS updates lagging behind physical movements, causing "
            "temporary data inconsistencies that appear as anomalies."
        ),
        "metadata": {"topic": "dc_operations", "type": "knowledge"},
    },
    {
        "content": (
            "SUPPLIER RELIABILITY FACTORS IN CPG: "
            "Key factors affecting supplier reliability: "
            "1) Supplier Tier — Tier 1 suppliers (large multinationals) typically 95%+ OTIF. "
            "Tier 2/3 suppliers may be 80-90% OTIF. "
            "2) Geographic risk — Single-source suppliers in disaster-prone areas carry higher "
            "risk. Import-dependent supply chains face port/customs variability. "
            "3) Financial health — Suppliers with tight cash flow may prioritize larger customers. "
            "4) Seasonal capacity — Agriculture-based raw materials have harvest cycles. "
            "5) Quality consistency — Variable quality leads to higher rejection rates and "
            "effective supply reduction. "
            "6) Communication maturity — EDI-connected suppliers have fewer order errors."
        ),
        "metadata": {"topic": "supplier", "type": "knowledge"},
    },
]


def initialize_knowledge_base():
    """Create and populate the ChromaDB knowledge base."""
    os.makedirs(config.CHROMA_PERSIST_DIR, exist_ok=True)

    client = chromadb.PersistentClient(path=config.CHROMA_PERSIST_DIR)

    # Delete existing collection if it exists
    try:
        client.delete_collection(config.CHROMA_COLLECTION_NAME)
    except Exception:
        pass

    collection = client.create_collection(
        name=config.CHROMA_COLLECTION_NAME,
        metadata={"description": "Supply chain domain knowledge for anomaly explanation"},
    )

    # Add documents
    ids = [f"doc_{i}" for i in range(len(KNOWLEDGE_DOCUMENTS))]
    documents = [doc["content"] for doc in KNOWLEDGE_DOCUMENTS]
    metadatas = [doc["metadata"] for doc in KNOWLEDGE_DOCUMENTS]

    collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
    )

    print(f"✅ Knowledge base initialized with {len(documents)} documents")
    print(f"   Persist directory: {config.CHROMA_PERSIST_DIR}")
    return collection


def search_knowledge(query: str, top_k: int = None) -> list[dict]:
    """Search the knowledge base for relevant information."""
    top_k = top_k or config.RAG_TOP_K

    client = chromadb.PersistentClient(path=config.CHROMA_PERSIST_DIR)
    collection = client.get_collection(config.CHROMA_COLLECTION_NAME)

    results = collection.query(
        query_texts=[query],
        n_results=top_k,
    )

    output = []
    for i in range(len(results["ids"][0])):
        output.append({
            "id": results["ids"][0][i],
            "content": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i] if results.get("distances") else None,
        })

    return output


if __name__ == "__main__":
    print("🔄 Initializing knowledge base...")
    initialize_knowledge_base()

    # Test search
    print("\n🔍 Test search: 'stockout root cause'")
    results = search_knowledge("stockout root cause", top_k=3)
    for r in results:
        print(f"   [{r['metadata']['topic']}] {r['content'][:80]}...")
