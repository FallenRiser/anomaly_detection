"""
Database helper functions for querying inventory data.
"""
import sqlite3
from typing import Optional

import pandas as pd

import config


def get_connection(db_path: str = None) -> sqlite3.Connection:
    """Get a SQLite database connection."""
    db_path = db_path or config.SQLITE_DB_PATH
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def get_anomalies(
    limit: int = 100,
    offset: int = 0,
    anomaly_type: str = None,
    severity: str = None,
    product_id: str = None,
    dc_id: str = None,
    date_from: str = None,
    date_to: str = None,
) -> list[dict]:
    """Fetch anomalies with optional filters."""
    conn = get_connection()
    query = """
        SELECT ir.*, al.anomaly_id, al.explanation, al.explained_at
        FROM inventory_records ir
        JOIN anomaly_log al ON ir.record_id = al.record_id
        WHERE ir.is_anomaly = 1
    """
    params = []

    if anomaly_type:
        query += " AND ir.anomaly_type = ?"
        params.append(anomaly_type)
    if severity:
        query += " AND ir.anomaly_severity = ?"
        params.append(severity)
    if product_id:
        query += " AND ir.product_id = ?"
        params.append(product_id)
    if dc_id:
        query += " AND ir.distribution_center_id = ?"
        params.append(dc_id)
    if date_from:
        query += " AND ir.date >= ?"
        params.append(date_from)
    if date_to:
        query += " AND ir.date <= ?"
        params.append(date_to)

    query += " ORDER BY ir.date DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_anomaly_by_id(anomaly_id: int) -> Optional[dict]:
    """Fetch a single anomaly by its anomaly_log ID."""
    conn = get_connection()
    row = conn.execute("""
        SELECT ir.*, al.anomaly_id, al.explanation, al.explained_at, al.analyst_notes
        FROM inventory_records ir
        JOIN anomaly_log al ON ir.record_id = al.record_id
        WHERE al.anomaly_id = ?
    """, (anomaly_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_anomaly_by_record_id(record_id: int) -> Optional[dict]:
    """Fetch anomaly info by record_id."""
    conn = get_connection()
    row = conn.execute("""
        SELECT ir.*, al.anomaly_id, al.explanation, al.explained_at
        FROM inventory_records ir
        JOIN anomaly_log al ON ir.record_id = al.record_id
        WHERE ir.record_id = ?
    """, (record_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_product_history(
    product_id: str,
    dc_id: str,
    date_center: str,
    days_before: int = 14,
    days_after: int = 7,
) -> list[dict]:
    """Get inventory history around a specific date for context."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM inventory_records
        WHERE product_id = ?
          AND distribution_center_id = ?
          AND date BETWEEN date(?, '-' || ? || ' days') AND date(?, '+' || ? || ' days')
        ORDER BY date
    """, (product_id, dc_id, date_center, days_before, date_center, days_after)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_context_for_anomaly(anomaly_id: int) -> dict:
    """Get full context for an anomaly: the record, surrounding history, and product/DC info."""
    anomaly = get_anomaly_by_id(anomaly_id)
    if not anomaly:
        return {}

    history = get_product_history(
        anomaly["product_id"],
        anomaly["distribution_center_id"],
        anomaly["date"],
    )

    conn = get_connection()
    product = dict(conn.execute(
        "SELECT * FROM products WHERE product_id = ?", (anomaly["product_id"],)
    ).fetchone())
    dc = dict(conn.execute(
        "SELECT * FROM distribution_centers WHERE dc_id = ?",
        (anomaly["distribution_center_id"],)
    ).fetchone())
    conn.close()

    return {
        "anomaly": anomaly,
        "history": history,
        "product": product,
        "distribution_center": dc,
    }


def get_dashboard_stats() -> dict:
    """Get summary statistics for the dashboard."""
    conn = get_connection()

    total = conn.execute("SELECT COUNT(*) FROM inventory_records").fetchone()[0]
    anomaly_count = conn.execute("SELECT COUNT(*) FROM anomaly_log").fetchone()[0]
    critical = conn.execute("SELECT COUNT(*) FROM anomaly_log WHERE anomaly_severity = 'critical'").fetchone()[0]
    unexplained = conn.execute("SELECT COUNT(*) FROM anomaly_log WHERE explanation IS NULL").fetchone()[0]

    by_type = conn.execute("""
        SELECT anomaly_type, COUNT(*) as count
        FROM anomaly_log GROUP BY anomaly_type ORDER BY count DESC
    """).fetchall()

    by_severity = conn.execute("""
        SELECT anomaly_severity, COUNT(*) as count
        FROM anomaly_log GROUP BY anomaly_severity ORDER BY count DESC
    """).fetchall()

    by_dc = conn.execute("""
        SELECT ir.distribution_center, COUNT(*) as count
        FROM anomaly_log al
        JOIN inventory_records ir ON al.record_id = ir.record_id
        GROUP BY ir.distribution_center ORDER BY count DESC
    """).fetchall()

    by_product = conn.execute("""
        SELECT ir.product_name, COUNT(*) as count
        FROM anomaly_log al
        JOIN inventory_records ir ON al.record_id = ir.record_id
        GROUP BY ir.product_name ORDER BY count DESC
        LIMIT 10
    """).fetchall()

    recent = conn.execute("""
        SELECT ir.*, al.anomaly_id
        FROM inventory_records ir
        JOIN anomaly_log al ON ir.record_id = al.record_id
        WHERE ir.is_anomaly = 1
        ORDER BY ir.date DESC LIMIT 10
    """).fetchall()

    conn.close()

    return {
        "total_records": total,
        "total_anomalies": anomaly_count,
        "critical_anomalies": critical,
        "unexplained_anomalies": unexplained,
        "by_type": [dict(r) for r in by_type],
        "by_severity": [dict(r) for r in by_severity],
        "by_dc": [dict(r) for r in by_dc],
        "by_product": [dict(r) for r in by_product],
        "recent_anomalies": [dict(r) for r in recent],
    }


def run_custom_query(sql: str) -> list[dict]:
    """Run a read-only SQL query. Only SELECT statements are allowed."""
    sql_stripped = sql.strip().upper()
    if not sql_stripped.startswith("SELECT"):
        raise ValueError("Only SELECT queries are allowed.")

    conn = get_connection()
    try:
        rows = conn.execute(sql).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def save_explanation(anomaly_id: int, explanation: str, causes: str, actions: str, confidence: float):
    """Save an AI-generated explanation to the database."""
    conn = get_connection()
    from datetime import datetime
    now = datetime.now().isoformat()

    conn.execute("""
        UPDATE anomaly_log SET explanation = ?, explained_at = ? WHERE anomaly_id = ?
    """, (explanation, now, anomaly_id))

    # Also get the record_id for the cache
    row = conn.execute("SELECT record_id FROM anomaly_log WHERE anomaly_id = ?", (anomaly_id,)).fetchone()
    if row:
        conn.execute("""
            INSERT INTO explanation_cache (record_id, explanation, probable_causes,
                                           recommended_actions, confidence_score)
            VALUES (?, ?, ?, ?, ?)
        """, (row["record_id"], explanation, causes, actions, confidence))

    conn.commit()
    conn.close()


def get_products_list() -> list[dict]:
    """Get list of all products."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM products ORDER BY product_name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_dc_list() -> list[dict]:
    """Get list of all distribution centers."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM distribution_centers ORDER BY dc_name").fetchall()
    conn.close()
    return [dict(r) for r in rows]
