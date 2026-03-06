"""
Synthetic CPG Inventory Data Generator.

Generates realistic inventory time-series data for Consumer Packaged Goods
across multiple distribution centers, with injected anomalies of various types.
"""
import os
import random
import sqlite3
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

import config


# ── Product & DC Definitions ───────────────────────────────────────────────

PRODUCTS = [
    {"id": "SKU001", "name": "Tide Laundry Detergent 3L",     "category": "Home Care",        "supplier": "P&G Supply Co",         "base_stock": 500,  "base_sales": 35,  "shelf_life_days": 730},
    {"id": "SKU002", "name": "Colgate MaxFresh Toothpaste",   "category": "Personal Care",    "supplier": "Colgate-Palmolive",     "base_stock": 800,  "base_sales": 55,  "shelf_life_days": 540},
    {"id": "SKU003", "name": "Lay's Classic Chips 200g",      "category": "Snacks",           "supplier": "PepsiCo Foods",         "base_stock": 1200, "base_sales": 90,  "shelf_life_days": 120},
    {"id": "SKU004", "name": "Amul Butter 500g",              "category": "Dairy",            "supplier": "Amul Dairy Co-op",      "base_stock": 600,  "base_sales": 45,  "shelf_life_days": 90},
    {"id": "SKU005", "name": "Maggi 2-Minute Noodles 12pk",   "category": "Ready-to-Eat",     "supplier": "Nestle India",          "base_stock": 1500, "base_sales": 120, "shelf_life_days": 270},
    {"id": "SKU006", "name": "Dove Body Wash 750ml",          "category": "Personal Care",    "supplier": "Hindustan Unilever",    "base_stock": 400,  "base_sales": 28,  "shelf_life_days": 730},
    {"id": "SKU007", "name": "Coca-Cola 2L Bottle",           "category": "Beverages",        "supplier": "Coca-Cola Bottlers",    "base_stock": 2000, "base_sales": 150, "shelf_life_days": 180},
    {"id": "SKU008", "name": "Parle-G Biscuits 800g",         "category": "Snacks",           "supplier": "Parle Products",        "base_stock": 1800, "base_sales": 130, "shelf_life_days": 180},
    {"id": "SKU009", "name": "Dettol Handwash 900ml",         "category": "Home Care",        "supplier": "Reckitt Benckiser",     "base_stock": 700,  "base_sales": 42,  "shelf_life_days": 730},
    {"id": "SKU010", "name": "Tropicana Orange Juice 1L",     "category": "Beverages",        "supplier": "PepsiCo Beverages",     "base_stock": 500,  "base_sales": 40,  "shelf_life_days": 60},
    {"id": "SKU011", "name": "Pampers Baby Diapers 72ct",     "category": "Baby Care",        "supplier": "P&G Supply Co",         "base_stock": 300,  "base_sales": 18,  "shelf_life_days": 1095},
    {"id": "SKU012", "name": "Nescafe Classic Coffee 200g",   "category": "Beverages",        "supplier": "Nestle India",          "base_stock": 600,  "base_sales": 38,  "shelf_life_days": 365},
    {"id": "SKU013", "name": "Surf Excel Matic 2kg",          "category": "Home Care",        "supplier": "Hindustan Unilever",    "base_stock": 450,  "base_sales": 30,  "shelf_life_days": 730},
    {"id": "SKU014", "name": "Mother Dairy Milk 1L",          "category": "Dairy",            "supplier": "Mother Dairy",          "base_stock": 1000, "base_sales": 200, "shelf_life_days": 7},
    {"id": "SKU015", "name": "Haldiram's Namkeen 400g",       "category": "Snacks",           "supplier": "Haldiram Foods",        "base_stock": 900,  "base_sales": 65,  "shelf_life_days": 150},
    {"id": "SKU016", "name": "Gillette Mach3 Razor 4pk",      "category": "Personal Care",    "supplier": "P&G Supply Co",         "base_stock": 250,  "base_sales": 12,  "shelf_life_days": 1825},
    {"id": "SKU017", "name": "Britannia Bread 400g",          "category": "Bakery",           "supplier": "Britannia Industries",  "base_stock": 800,  "base_sales": 160, "shelf_life_days": 5},
    {"id": "SKU018", "name": "Red Bull Energy Drink 250ml",   "category": "Beverages",        "supplier": "Red Bull India",        "base_stock": 600,  "base_sales": 35,  "shelf_life_days": 365},
    {"id": "SKU019", "name": "Whisper Ultra Pads 30ct",       "category": "Personal Care",    "supplier": "P&G Supply Co",         "base_stock": 500,  "base_sales": 25,  "shelf_life_days": 1095},
    {"id": "SKU020", "name": "Cadbury Dairy Milk 150g",       "category": "Confectionery",    "supplier": "Mondelez India",        "base_stock": 1100, "base_sales": 85,  "shelf_life_days": 270},
]

DISTRIBUTION_CENTERS = [
    {"id": "DC01", "name": "Mumbai Central Warehouse",   "region": "West",  "capacity": 50000},
    {"id": "DC02", "name": "Delhi NCR Hub",              "region": "North", "capacity": 45000},
    {"id": "DC03", "name": "Bengaluru South DC",         "region": "South", "capacity": 40000},
    {"id": "DC04", "name": "Kolkata East Center",        "region": "East",  "capacity": 35000},
    {"id": "DC05", "name": "Chennai Logistics Park",     "region": "South", "capacity": 38000},
]

ANOMALY_TYPES = ["stockout", "overstock", "demand_spike", "supply_delay", "shrinkage", "forecast_error"]


# ── Seasonal & Regional Multipliers ────────────────────────────────────────

def _seasonal_factor(date: datetime, category: str) -> float:
    """Apply realistic seasonal patterns based on product category."""
    month = date.month
    factors = {
        "Beverages":    {1: 0.7, 2: 0.75, 3: 0.9, 4: 1.1, 5: 1.3, 6: 1.5, 7: 1.4, 8: 1.3, 9: 1.1, 10: 1.0, 11: 0.9, 12: 0.8},
        "Dairy":        {1: 1.0, 2: 1.0, 3: 1.05, 4: 1.1, 5: 1.15, 6: 1.2, 7: 1.15, 8: 1.1, 9: 1.05, 10: 1.0, 11: 1.0, 12: 1.0},
        "Snacks":       {1: 1.0, 2: 1.0, 3: 1.0, 4: 1.0, 5: 1.0, 6: 1.0, 7: 1.05, 8: 1.05, 9: 1.1, 10: 1.3, 11: 1.5, 12: 1.3},
        "Home Care":    {1: 1.1, 2: 1.0, 3: 1.0, 4: 0.9, 5: 0.9, 6: 0.9, 7: 0.9, 8: 0.9, 9: 1.0, 10: 1.1, 11: 1.2, 12: 1.2},
        "Confectionery":{1: 0.9, 2: 1.3, 3: 1.0, 4: 1.0, 5: 1.0, 6: 0.9, 7: 0.9, 8: 1.0, 9: 1.0, 10: 1.2, 11: 1.4, 12: 1.5},
    }
    return factors.get(category, {}).get(month, 1.0)


def _regional_factor(region: str, category: str) -> float:
    """Regional demand variation."""
    factors = {
        ("North", "Dairy"): 1.2, ("North", "Beverages"): 0.9,
        ("South", "Beverages"): 1.2, ("South", "Snacks"): 1.1,
        ("West", "Home Care"): 1.15, ("East", "Snacks"): 1.1,
    }
    return factors.get((region, category), 1.0)


# ── Anomaly Injection ──────────────────────────────────────────────────────

def _inject_anomaly(row: dict, product: dict, anomaly_type: str) -> dict:
    """Modify row data to reflect an anomaly and add metadata."""
    row["is_anomaly"] = 1
    row["anomaly_type"] = anomaly_type

    if anomaly_type == "stockout":
        row["stock_level"] = random.randint(0, max(5, int(product["base_stock"] * 0.02)))
        row["anomaly_severity"] = "critical" if row["stock_level"] == 0 else "high"

    elif anomaly_type == "overstock":
        multiplier = random.uniform(2.5, 5.0)
        row["stock_level"] = int(product["base_stock"] * multiplier)
        row["anomaly_severity"] = "high" if multiplier > 3.5 else "medium"

    elif anomaly_type == "demand_spike":
        spike = random.uniform(2.5, 6.0)
        row["sales_rate"] = round(product["base_sales"] * spike, 1)
        row["stock_level"] = max(0, row["stock_level"] - int(row["sales_rate"] * random.randint(1, 3)))
        row["anomaly_severity"] = "high" if spike > 4.0 else "medium"

    elif anomaly_type == "supply_delay":
        row["lead_time_days"] = row["lead_time_days"] * random.randint(2, 5)
        row["stock_level"] = max(0, int(row["stock_level"] * random.uniform(0.2, 0.5)))
        row["anomaly_severity"] = "high" if row["lead_time_days"] > 20 else "medium"

    elif anomaly_type == "shrinkage":
        loss = random.uniform(0.15, 0.40)
        row["stock_level"] = max(0, int(row["stock_level"] * (1 - loss)))
        row["anomaly_severity"] = "high" if loss > 0.30 else "medium"

    elif anomaly_type == "forecast_error":
        direction = random.choice(["over", "under"])
        error_pct = random.uniform(0.4, 0.8)
        if direction == "over":
            row["demand_forecast"] = round(row["sales_rate"] * (1 + error_pct), 1)
            row["stock_level"] = int(row["stock_level"] * random.uniform(1.5, 2.5))
        else:
            row["demand_forecast"] = round(row["sales_rate"] * (1 - error_pct), 1)
            row["stock_level"] = max(0, int(row["stock_level"] * random.uniform(0.3, 0.6)))
        row["anomaly_severity"] = "high" if error_pct > 0.6 else "medium"

    return row


# ── Main Generator ─────────────────────────────────────────────────────────

def generate_inventory_data() -> pd.DataFrame:
    """Generate synthetic CPG inventory data with realistic anomalies."""
    random.seed(42)
    np.random.seed(42)

    start = datetime.strptime(config.DATA_START_DATE, "%Y-%m-%d")
    end = datetime.strptime(config.DATA_END_DATE, "%Y-%m-%d")
    dates = [start + timedelta(days=i) for i in range((end - start).days + 1)]

    records = []
    record_id = 1

    for product in PRODUCTS:
        for dc in DISTRIBUTION_CENTERS:
            prev_stock = product["base_stock"] * random.uniform(0.8, 1.2)
            base_lead = random.randint(3, 10)

            for date in dates:
                seasonal = _seasonal_factor(date, product["category"])
                regional = _regional_factor(dc["region"], product["category"])
                day_noise = np.random.normal(1.0, 0.08)

                sales = max(0, round(product["base_sales"] * seasonal * regional * day_noise, 1))
                forecast = round(sales * np.random.normal(1.0, 0.12), 1)

                # Simulate natural stock dynamics
                reorder_point = product["base_sales"] * base_lead * 1.2
                replenishment = 0
                if prev_stock <= reorder_point:
                    replenishment = product["base_stock"] * random.uniform(0.8, 1.2)

                stock = max(0, int(prev_stock - sales + replenishment))

                row = {
                    "record_id": record_id,
                    "date": date.strftime("%Y-%m-%d"),
                    "product_id": product["id"],
                    "product_name": product["name"],
                    "category": product["category"],
                    "distribution_center_id": dc["id"],
                    "distribution_center": dc["name"],
                    "region": dc["region"],
                    "stock_level": stock,
                    "reorder_point": int(reorder_point),
                    "sales_rate": sales,
                    "demand_forecast": max(0, forecast),
                    "lead_time_days": base_lead,
                    "supplier": product["supplier"],
                    "is_anomaly": 0,
                    "anomaly_type": None,
                    "anomaly_severity": None,
                }

                # Inject anomalies with configured probability
                if random.random() < config.ANOMALY_RATE:
                    anomaly_type = random.choice(ANOMALY_TYPES)
                    row = _inject_anomaly(row, product, anomaly_type)

                records.append(row)
                prev_stock = row["stock_level"]
                record_id += 1

    df = pd.DataFrame(records)
    return df


def save_to_csv(df: pd.DataFrame, path: str = None):
    """Save DataFrame to CSV."""
    path = path or config.CSV_OUTPUT_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, index=False)
    print(f"✅ Saved {len(df)} records to {path}")
    return path


def save_to_sqlite(df: pd.DataFrame, db_path: str = None):
    """Save DataFrame to SQLite database with proper schema."""
    db_path = db_path or config.SQLITE_DB_PATH
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # ── Create tables ───────────────────────────────────────────────────
    cursor.executescript("""
        DROP TABLE IF EXISTS inventory_records;
        DROP TABLE IF EXISTS products;
        DROP TABLE IF EXISTS distribution_centers;
        DROP TABLE IF EXISTS anomaly_log;
        DROP TABLE IF EXISTS explanation_cache;

        CREATE TABLE products (
            product_id TEXT PRIMARY KEY,
            product_name TEXT NOT NULL,
            category TEXT NOT NULL,
            supplier TEXT NOT NULL,
            base_stock INTEGER,
            base_sales_rate REAL,
            shelf_life_days INTEGER
        );

        CREATE TABLE distribution_centers (
            dc_id TEXT PRIMARY KEY,
            dc_name TEXT NOT NULL,
            region TEXT NOT NULL,
            capacity INTEGER
        );

        CREATE TABLE inventory_records (
            record_id INTEGER PRIMARY KEY,
            date TEXT NOT NULL,
            product_id TEXT NOT NULL,
            product_name TEXT,
            category TEXT,
            distribution_center_id TEXT NOT NULL,
            distribution_center TEXT,
            region TEXT,
            stock_level INTEGER,
            reorder_point INTEGER,
            sales_rate REAL,
            demand_forecast REAL,
            lead_time_days INTEGER,
            supplier TEXT,
            is_anomaly INTEGER DEFAULT 0,
            anomaly_type TEXT,
            anomaly_severity TEXT,
            FOREIGN KEY (product_id) REFERENCES products(product_id),
            FOREIGN KEY (distribution_center_id) REFERENCES distribution_centers(dc_id)
        );

        CREATE TABLE anomaly_log (
            anomaly_id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            product_id TEXT NOT NULL,
            distribution_center_id TEXT NOT NULL,
            anomaly_type TEXT NOT NULL,
            anomaly_severity TEXT,
            explanation TEXT,
            explained_at TEXT,
            analyst_notes TEXT,
            FOREIGN KEY (record_id) REFERENCES inventory_records(record_id)
        );

        CREATE TABLE explanation_cache (
            cache_id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_id INTEGER NOT NULL,
            explanation TEXT NOT NULL,
            probable_causes TEXT,
            recommended_actions TEXT,
            confidence_score REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (record_id) REFERENCES inventory_records(record_id)
        );

        CREATE INDEX idx_inv_date ON inventory_records(date);
        CREATE INDEX idx_inv_product ON inventory_records(product_id);
        CREATE INDEX idx_inv_dc ON inventory_records(distribution_center_id);
        CREATE INDEX idx_inv_anomaly ON inventory_records(is_anomaly);
        CREATE INDEX idx_anomaly_log_record ON anomaly_log(record_id);
    """)

    # ── Insert products ─────────────────────────────────────────────────
    for p in PRODUCTS:
        cursor.execute(
            "INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?)",
            (p["id"], p["name"], p["category"], p["supplier"],
             p["base_stock"], p["base_sales"], p["shelf_life_days"])
        )

    # ── Insert DCs ──────────────────────────────────────────────────────
    for dc in DISTRIBUTION_CENTERS:
        cursor.execute(
            "INSERT INTO distribution_centers VALUES (?, ?, ?, ?)",
            (dc["id"], dc["name"], dc["region"], dc["capacity"])
        )

    # ── Insert inventory records ────────────────────────────────────────
    df.to_sql("inventory_records", conn, if_exists="replace", index=False)

    # ── Populate anomaly_log from inventory_records ─────────────────────
    cursor.execute("""
        INSERT INTO anomaly_log (record_id, date, product_id, distribution_center_id,
                                  anomaly_type, anomaly_severity)
        SELECT record_id, date, product_id, distribution_center_id,
               anomaly_type, anomaly_severity
        FROM inventory_records
        WHERE is_anomaly = 1
    """)

    conn.commit()

    anomaly_count = cursor.execute("SELECT COUNT(*) FROM anomaly_log").fetchone()[0]
    total_count = cursor.execute("SELECT COUNT(*) FROM inventory_records").fetchone()[0]
    print(f"✅ SQLite DB created at {db_path}")
    print(f"   Total records: {total_count}")
    print(f"   Anomalies: {anomaly_count} ({anomaly_count/total_count*100:.1f}%)")

    conn.close()


# ── Entry Point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("🔄 Generating synthetic CPG inventory data...")
    df = generate_inventory_data()
    save_to_csv(df)
    save_to_sqlite(df)

    # Print summary stats
    print("\n📊 Data Summary:")
    print(f"   Date range: {df['date'].min()} to {df['date'].max()}")
    print(f"   Products: {df['product_id'].nunique()}")
    print(f"   Distribution Centers: {df['distribution_center_id'].nunique()}")
    print(f"   Anomaly types: {df[df['is_anomaly']==1]['anomaly_type'].value_counts().to_dict()}")
