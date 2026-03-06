"""
Flask Web Application for Supply Chain Anomaly Explanation Assistant.
"""
import os
import json
import traceback
from datetime import datetime

from flask import Flask, render_template, request, jsonify, redirect, url_for
import pandas as pd

import config
import database
from agent import explain_anomaly

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB upload limit


# ── Dashboard ──────────────────────────────────────────────────────────────

@app.route("/")
def dashboard():
    """Main dashboard with anomaly overview."""
    stats = database.get_dashboard_stats()
    return render_template("dashboard.html", stats=stats)


# ── Anomaly List ───────────────────────────────────────────────────────────

@app.route("/anomalies")
def anomaly_list():
    """Filterable list of all anomalies."""
    filters = {
        "anomaly_type": request.args.get("type"),
        "severity": request.args.get("severity"),
        "product_id": request.args.get("product"),
        "dc_id": request.args.get("dc"),
        "date_from": request.args.get("date_from"),
        "date_to": request.args.get("date_to"),
    }
    page = int(request.args.get("page", 1))
    per_page = 25
    offset = (page - 1) * per_page

    anomalies = database.get_anomalies(limit=per_page, offset=offset, **filters)
    products = database.get_products_list()
    dcs = database.get_dc_list()

    return render_template(
        "anomalies.html",
        anomalies=anomalies,
        products=products,
        dcs=dcs,
        filters=filters,
        page=page,
    )


# ── Anomaly Detail ─────────────────────────────────────────────────────────

@app.route("/anomaly/<int:anomaly_id>")
def anomaly_detail(anomaly_id: int):
    """Detail view for a specific anomaly with explanation."""
    context = database.get_context_for_anomaly(anomaly_id)
    if not context:
        return "Anomaly not found", 404
    return render_template("anomaly_detail.html", context=context)


# ── AI Explanation Endpoint ────────────────────────────────────────────────

@app.route("/explain", methods=["POST"])
def explain():
    """Trigger AI explanation for an anomaly."""
    anomaly_id = request.json.get("anomaly_id")
    if not anomaly_id:
        return jsonify({"error": "anomaly_id is required"}), 400

    try:
        result = explain_anomaly(int(anomaly_id))
        return jsonify(result)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ── CSV Upload ─────────────────────────────────────────────────────────────

@app.route("/upload", methods=["GET", "POST"])
def upload():
    """Upload custom CSV data."""
    if request.method == "GET":
        return render_template("upload.html")

    file = request.files.get("file")
    if not file or not file.filename.endswith(".csv"):
        return render_template("upload.html", error="Please upload a valid CSV file.")

    try:
        df = pd.read_csv(file)
        required_cols = {"date", "product_id", "stock_level", "is_anomaly"}
        if not required_cols.issubset(set(df.columns)):
            missing = required_cols - set(df.columns)
            return render_template(
                "upload.html",
                error=f"Missing required columns: {', '.join(missing)}"
            )

        # Import the data generation module for DB save
        from generate_data import save_to_sqlite

        # Add record_id if not present
        if "record_id" not in df.columns:
            conn = database.get_connection()
            max_id = conn.execute("SELECT MAX(record_id) FROM inventory_records").fetchone()[0] or 0
            conn.close()
            df["record_id"] = range(max_id + 1, max_id + len(df) + 1)

        # Fill missing columns
        for col in ["product_name", "category", "distribution_center_id", "distribution_center",
                     "region", "reorder_point", "sales_rate", "demand_forecast",
                     "lead_time_days", "supplier", "anomaly_type", "anomaly_severity"]:
            if col not in df.columns:
                df[col] = None

        save_to_sqlite(df)

        return render_template(
            "upload.html",
            success=f"Successfully imported {len(df)} records ({df['is_anomaly'].sum()} anomalies)."
        )
    except Exception as e:
        traceback.print_exc()
        return render_template("upload.html", error=f"Error processing file: {str(e)}")


# ── API Endpoints ──────────────────────────────────────────────────────────

@app.route("/api/anomalies")
def api_anomalies():
    """JSON API for anomaly list."""
    filters = {
        "anomaly_type": request.args.get("type"),
        "severity": request.args.get("severity"),
        "product_id": request.args.get("product"),
        "dc_id": request.args.get("dc"),
        "date_from": request.args.get("date_from"),
        "date_to": request.args.get("date_to"),
    }
    limit = int(request.args.get("limit", 100))
    offset = int(request.args.get("offset", 0))

    anomalies = database.get_anomalies(limit=limit, offset=offset, **filters)
    return jsonify({"anomalies": anomalies, "count": len(anomalies)})


@app.route("/api/stats")
def api_stats():
    """JSON API for dashboard statistics."""
    stats = database.get_dashboard_stats()
    return jsonify(stats)


@app.route("/api/anomaly/<int:anomaly_id>/history")
def api_anomaly_history(anomaly_id: int):
    """JSON API for anomaly context/history."""
    context = database.get_context_for_anomaly(anomaly_id)
    if not context:
        return jsonify({"error": "Not found"}), 404
    return jsonify(context)


# ── Entry Point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(
        host=config.FLASK_HOST,
        port=config.FLASK_PORT,
        debug=config.FLASK_DEBUG,
    )
