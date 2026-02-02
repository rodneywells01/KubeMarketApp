from flask import Flask, jsonify, request
from auth import auth, is_auth_configured
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configure secret key for session management
# In production, this should be set via environment variable
app.secret_key = os.environ.get("FLASK_SECRET_KEY", os.urandom(24))

# Check authentication configuration on startup
if is_auth_configured():
    logger.info("✓ API authentication is configured and enabled")
else:
    logger.warning("⚠ API authentication is NOT configured - API endpoints are unprotected!")


# ============================================================================
# Net Worth API Endpoints
# ============================================================================

@app.route("/marketapi/v1/networth", methods=["GET"])
@auth.login_required
def get_net_worth():
    """
    Get all net worth tracking data from Google Sheets.
    
    Query Parameters:
        start_date: Filter entries starting from this date (YYYY-MM-DD)
        end_date: Filter entries up to this date (YYYY-MM-DD)
        latest: If 'true', return only the most recent entry
    
    Returns:
        JSON with net worth data and metadata
    """
    from datetime import datetime
    try:
        from services.google_sheets import load_net_worth_from_sheets, GoogleSheetsError
    except ImportError as e:
        return jsonify({
            "error": "Google Sheets dependencies not installed",
            "details": str(e),
            "hint": "Install with: pip install google-api-python-client google-auth"
        }), 500
    
    try:
        dataset = load_net_worth_from_sheets()
        
        # Handle query parameters
        latest_only = request.args.get("latest", "").lower() == "true"
        start_date_str = request.args.get("start_date")
        end_date_str = request.args.get("end_date")
        
        if latest_only:
            latest = dataset.get_latest_entry()
            if latest:
                return jsonify({
                    "success": True,
                    "data": latest.to_dict(),
                    "source": {
                        "sheet_id": dataset.source_sheet_id,
                        "sheet_name": dataset.source_sheet_name,
                        "last_updated": dataset.last_updated.isoformat() if dataset.last_updated else None
                    }
                })
            else:
                return jsonify({"success": False, "error": "No data found"}), 404
        
        # Apply date filters if provided
        entries = dataset.entries
        
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                entries = [e for e in entries if e.date >= start_date]
            except ValueError:
                return jsonify({"error": f"Invalid start_date format: {start_date_str}. Use YYYY-MM-DD"}), 400
        
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                entries = [e for e in entries if e.date <= end_date]
            except ValueError:
                return jsonify({"error": f"Invalid end_date format: {end_date_str}. Use YYYY-MM-DD"}), 400
        
        # Sort by date
        entries = sorted(entries, key=lambda e: e.date)
        
        return jsonify({
            "success": True,
            "data": [entry.to_dict() for entry in entries],
            "count": len(entries),
            "source": {
                "sheet_id": dataset.source_sheet_id,
                "sheet_name": dataset.source_sheet_name,
                "last_updated": dataset.last_updated.isoformat() if dataset.last_updated else None
            }
        })
    
    except GoogleSheetsError as e:
        logger.error(f"Google Sheets error: {e}")
        return jsonify({
            "success": False,
            "error": "Failed to load data from Google Sheets",
            "details": str(e)
        }), 500
    except Exception as e:
        logger.exception("Unexpected error in get_net_worth")
        return jsonify({
            "success": False,
            "error": "Internal server error",
            "details": str(e)
        }), 500


@app.route("/marketapi/v1/networth/summary", methods=["GET"])
@auth.login_required
def get_net_worth_summary():
    """
    Get a summary of net worth data including latest values and trends.
    
    Returns:
        JSON with summary statistics
    """
    from datetime import datetime, timedelta
    try:
        from services.google_sheets import load_net_worth_from_sheets, GoogleSheetsError
    except ImportError as e:
        return jsonify({
            "error": "Google Sheets dependencies not installed",
            "details": str(e)
        }), 500
    
    try:
        dataset = load_net_worth_from_sheets()
        
        if not dataset.entries:
            return jsonify({"success": False, "error": "No data found"}), 404
        
        # Sort entries by date
        sorted_entries = sorted(dataset.entries, key=lambda e: e.date)
        latest = sorted_entries[-1]
        
        # Calculate summary stats
        summary = {
            "latest": {
                "date": latest.date.isoformat(),
                "net_worth": str(latest.net_worth) if latest.net_worth else None,
                "investible_assets": str(latest.investible_assets) if latest.investible_assets else None,
                "semi_liquid_assets": str(latest.semi_liquid_assets) if latest.semi_liquid_assets else None,
            },
            "ytd": {
                "change_dollars": str(latest.ytd_change_dollars) if latest.ytd_change_dollars else None,
                "change_percent": str(latest.ytd_change_percent) if latest.ytd_change_percent else None,
            },
            "withdrawals": {
                "three_percent": str(latest.withdrawal_3_percent) if latest.withdrawal_3_percent else None,
                "four_percent": str(latest.withdrawal_4_percent) if latest.withdrawal_4_percent else None,
            },
            "projections": {
                "eight_percent_growth": str(latest.growth_8_percent) if latest.growth_8_percent else None,
            },
            "total_entries": len(dataset.entries),
            "date_range": {
                "earliest": sorted_entries[0].date.isoformat(),
                "latest": sorted_entries[-1].date.isoformat(),
            }
        }
        
        # Get account breakdown from latest entry
        account_balances = latest.get_account_balances()
        summary["accounts"] = {k: str(v) for k, v in account_balances.items()}
        
        return jsonify({
            "success": True,
            "summary": summary,
            "source": {
                "sheet_id": dataset.source_sheet_id,
                "sheet_name": dataset.source_sheet_name,
                "last_updated": dataset.last_updated.isoformat() if dataset.last_updated else None
            }
        })
    
    except GoogleSheetsError as e:
        logger.error(f"Google Sheets error: {e}")
        return jsonify({
            "success": False,
            "error": "Failed to load data from Google Sheets",
            "details": str(e)
        }), 500
    except Exception as e:
        logger.exception("Unexpected error in get_net_worth_summary")
        return jsonify({
            "success": False,
            "error": "Internal server error",
            "details": str(e)
        }), 500


@app.route("/marketapi/v1/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "service": "MarketApp"})


@app.route("/marketapi/v1/networth/chart/timeseries", methods=["GET"])
@auth.login_required
def get_net_worth_timeseries():
    """
    Get time series data optimized for charting.
    
    Query Parameters:
        period: '1m', '3m', '6m', '1y', 'ytd', 'all' (default: 'all')
        metrics: comma-separated list of metrics to include
                 (net_worth, investible_assets, semi_liquid_assets)
    
    Returns:
        JSON with labels (dates) and datasets for Chart.js
    """
    from datetime import datetime, timedelta
    from decimal import Decimal
    
    try:
        from services.google_sheets import load_net_worth_from_sheets, GoogleSheetsError
    except ImportError as e:
        return jsonify({"error": "Google Sheets dependencies not installed"}), 500
    
    try:
        dataset = load_net_worth_from_sheets()
        
        if not dataset.entries:
            return jsonify({"success": False, "error": "No data found"}), 404
        
        # Parse period parameter
        period = request.args.get("period", "all").lower()
        today = datetime.now().date()
        
        period_map = {
            "1m": today - timedelta(days=30),
            "3m": today - timedelta(days=90),
            "6m": today - timedelta(days=180),
            "1y": today - timedelta(days=365),
            "ytd": today.replace(month=1, day=1),
            "all": None
        }
        
        start_date = period_map.get(period)
        
        # Filter and sort entries
        entries = sorted(dataset.entries, key=lambda e: e.date)
        if start_date:
            entries = [e for e in entries if e.date >= start_date]
        
        # Parse metrics parameter
        metrics_param = request.args.get("metrics", "net_worth")
        requested_metrics = [m.strip() for m in metrics_param.split(",")]
        
        # Build response data
        labels = [entry.date.isoformat() for entry in entries]
        
        def to_float(val):
            if val is None:
                return None
            return float(val) if isinstance(val, Decimal) else val
        
        datasets = {}
        metric_configs = {
            "net_worth": {"label": "Net Worth", "color": "#667eea"},
            "investible_assets": {"label": "Investible Assets", "color": "#28a745"},
            "semi_liquid_assets": {"label": "Semi-Liquid Assets", "color": "#17a2b8"},
            "daily_net_worth_change": {"label": "Daily Change", "color": "#ffc107"},
        }
        
        for metric in requested_metrics:
            if metric in metric_configs:
                config = metric_configs[metric]
                datasets[metric] = {
                    "label": config["label"],
                    "data": [to_float(getattr(entry, metric, None)) for entry in entries],
                    "borderColor": config["color"],
                    "backgroundColor": config["color"] + "20",
                }
        
        return jsonify({
            "success": True,
            "labels": labels,
            "datasets": datasets,
            "period": period,
            "dataPoints": len(entries)
        })
    
    except Exception as e:
        logger.exception("Error in get_net_worth_timeseries")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/marketapi/v1/networth/chart/allocation", methods=["GET"])
@auth.login_required
def get_account_allocation():
    """
    Get account allocation data for pie/donut charts.
    
    Returns:
        JSON with account names, values, and percentages
    """
    try:
        from services.google_sheets import load_net_worth_from_sheets, GoogleSheetsError
    except ImportError as e:
        return jsonify({"error": "Google Sheets dependencies not installed"}), 500
    
    try:
        dataset = load_net_worth_from_sheets()
        
        if not dataset.entries:
            return jsonify({"success": False, "error": "No data found"}), 404
        
        latest = dataset.get_latest_entry()
        balances = latest.get_account_balances()
        
        # Filter out zero/negative values and sort by value
        positive_balances = {k: float(v) for k, v in balances.items() if v and float(v) > 0}
        sorted_accounts = sorted(positive_balances.items(), key=lambda x: x[1], reverse=True)
        
        total = sum(positive_balances.values())
        
        # Color palette for accounts
        colors = [
            "#667eea", "#764ba2", "#28a745", "#17a2b8", "#ffc107",
            "#dc3545", "#6f42c1", "#20c997", "#fd7e14", "#6c757d", "#e83e8c"
        ]
        
        allocation = []
        for i, (account, value) in enumerate(sorted_accounts):
            allocation.append({
                "account": account,
                "value": value,
                "percentage": round((value / total) * 100, 2) if total > 0 else 0,
                "color": colors[i % len(colors)]
            })
        
        return jsonify({
            "success": True,
            "date": latest.date.isoformat(),
            "total": total,
            "allocation": allocation,
            "labels": [a["account"] for a in allocation],
            "data": [a["value"] for a in allocation],
            "colors": [a["color"] for a in allocation]
        })
    
    except Exception as e:
        logger.exception("Error in get_account_allocation")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/marketapi/v1/networth/chart/trends", methods=["GET"])
@auth.login_required
def get_account_trends():
    """
    Get historical trends for each account (for stacked area chart).
    
    Query Parameters:
        period: '1m', '3m', '6m', '1y', 'ytd', 'all' (default: '6m')
    
    Returns:
        JSON with time series data per account
    """
    from datetime import datetime, timedelta
    
    try:
        from services.google_sheets import load_net_worth_from_sheets, GoogleSheetsError
    except ImportError as e:
        return jsonify({"error": "Google Sheets dependencies not installed"}), 500
    
    try:
        dataset = load_net_worth_from_sheets()
        
        if not dataset.entries:
            return jsonify({"success": False, "error": "No data found"}), 404
        
        # Parse period
        period = request.args.get("period", "6m").lower()
        today = datetime.now().date()
        
        period_map = {
            "1m": today - timedelta(days=30),
            "3m": today - timedelta(days=90),
            "6m": today - timedelta(days=180),
            "1y": today - timedelta(days=365),
            "ytd": today.replace(month=1, day=1),
            "all": None
        }
        
        start_date = period_map.get(period)
        
        entries = sorted(dataset.entries, key=lambda e: e.date)
        if start_date:
            entries = [e for e in entries if e.date >= start_date]
        
        labels = [entry.date.isoformat() for entry in entries]
        
        # Account configurations
        account_configs = [
            ("etrade", "E*TRADE", "#667eea"),
            ("crypto", "Crypto", "#f7931a"),
            ("fidelity", "Fidelity", "#4caf50"),
            ("thinkorswim", "thinkorswim", "#00bcd4"),
            ("tradestation", "TradeStation", "#9c27b0"),
            ("capital_one", "Capital One", "#dc3545"),
            ("nfts", "NFTs", "#e91e63"),
            ("car", "Car", "#607d8b"),
            ("misc", "Misc", "#795548"),
            ("inheritance", "Inheritance", "#009688"),
        ]
        
        def to_float(val):
            if val is None:
                return 0
            return float(val)
        
        datasets = []
        for attr, label, color in account_configs:
            data = [to_float(getattr(entry, attr, None)) for entry in entries]
            # Only include if there's actual data
            if any(d > 0 for d in data):
                datasets.append({
                    "label": label,
                    "data": data,
                    "backgroundColor": color + "80",
                    "borderColor": color,
                    "fill": True
                })
        
        return jsonify({
            "success": True,
            "labels": labels,
            "datasets": datasets,
            "period": period
        })
    
    except Exception as e:
        logger.exception("Error in get_account_trends")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/marketapi/v1/networth/retirement", methods=["GET"])
@auth.login_required
def get_retirement_metrics():
    """
    Get retirement planning metrics and projections.
    
    Returns:
        JSON with FIRE metrics, withdrawal scenarios, and projections
    """
    from decimal import Decimal
    
    try:
        from services.google_sheets import load_net_worth_from_sheets, GoogleSheetsError
    except ImportError as e:
        return jsonify({"error": "Google Sheets dependencies not installed"}), 500
    
    try:
        dataset = load_net_worth_from_sheets()
        
        if not dataset.entries:
            return jsonify({"success": False, "error": "No data found"}), 404
        
        latest = dataset.get_latest_entry()
        
        def to_float(val):
            if val is None:
                return None
            return float(val)
        
        net_worth = to_float(latest.net_worth) or 0
        living_expenses = to_float(latest.living_expenses) or 0
        retirement_spending = to_float(latest.retirement_spending) or living_expenses
        
        # Calculate FIRE metrics
        fire_number_25x = retirement_spending * 25 if retirement_spending else None
        fire_number_33x = retirement_spending * 33 if retirement_spending else None
        fire_progress_25x = (net_worth / fire_number_25x * 100) if fire_number_25x else None
        fire_progress_33x = (net_worth / fire_number_33x * 100) if fire_number_33x else None
        
        # Years of expenses covered
        years_covered = net_worth / retirement_spending if retirement_spending > 0 else None
        
        # Withdrawal scenarios
        withdrawal_scenarios = {
            "conservative_3pct": {
                "rate": 3,
                "annual": to_float(latest.withdrawal_3_percent),
                "monthly": to_float(latest.withdrawal_3_percent) / 12 if latest.withdrawal_3_percent else None,
            },
            "standard_4pct": {
                "rate": 4,
                "annual": to_float(latest.withdrawal_4_percent),
                "monthly": to_float(latest.withdrawal_4_percent) / 12 if latest.withdrawal_4_percent else None,
            },
            "aggressive_5pct": {
                "rate": 5,
                "annual": net_worth * 0.05,
                "monthly": net_worth * 0.05 / 12,
            }
        }
        
        # Growth projections (compound growth)
        projections = []
        growth_rate = 0.08
        current = net_worth
        for year in range(1, 11):
            current = current * (1 + growth_rate)
            projections.append({
                "year": year,
                "projected_value": round(current, 2),
                "withdrawal_4pct": round(current * 0.04, 2)
            })
        
        return jsonify({
            "success": True,
            "date": latest.date.isoformat(),
            "current": {
                "net_worth": net_worth,
                "living_expenses": living_expenses,
                "retirement_spending": retirement_spending,
            },
            "fire": {
                "number_25x": fire_number_25x,
                "number_33x": fire_number_33x,
                "progress_25x_percent": round(fire_progress_25x, 2) if fire_progress_25x else None,
                "progress_33x_percent": round(fire_progress_33x, 2) if fire_progress_33x else None,
                "years_of_expenses": round(years_covered, 1) if years_covered else None,
            },
            "withdrawals": withdrawal_scenarios,
            "projections_8pct": projections
        })
    
    except Exception as e:
        logger.exception("Error in get_retirement_metrics")
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================================
# Dashboard UI
# ============================================================================

@app.route("/")
@app.route("/marketapi")
@app.route("/dashboard")
@auth.login_required
def dashboard():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Net Worth Dashboard</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns"></script>
        <style>
            :root {
                --primary: #667eea;
                --primary-dark: #764ba2;
                --success: #28a745;
                --danger: #dc3545;
                --warning: #ffc107;
                --info: #17a2b8;
                --dark: #343a40;
                --light: #f8f9fa;
                --gray: #6c757d;
                --card-shadow: 0 4px 6px rgba(0, 0, 0, 0.07), 0 1px 3px rgba(0, 0, 0, 0.1);
                --card-shadow-hover: 0 10px 25px rgba(0, 0, 0, 0.15);
            }
            
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, Oxygen, Ubuntu, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                color: var(--dark);
            }
            
            .app-container {
                min-height: 100vh;
                background: #f0f2f5;
            }
            
            /* Header */
            .header {
                background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
                color: white;
                padding: 20px 30px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            
            .header h1 {
                font-size: 1.8em;
                font-weight: 600;
            }
            
            .header-subtitle {
                opacity: 0.9;
                font-size: 0.9em;
                margin-top: 4px;
            }
            
            .header-actions {
                display: flex;
                gap: 10px;
            }
            
            .btn {
                padding: 10px 20px;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                font-weight: 500;
                transition: all 0.2s;
                font-size: 0.9em;
            }
            
            .btn-outline {
                background: transparent;
                border: 2px solid rgba(255,255,255,0.5);
                color: white;
            }
            
            .btn-outline:hover {
                background: rgba(255,255,255,0.1);
                border-color: white;
            }
            
            .btn-primary {
                background: white;
                color: var(--primary);
            }
            
            .btn-primary:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            }
            
            /* Main Content */
            .main-content {
                padding: 30px;
                max-width: 1600px;
                margin: 0 auto;
            }
            
            /* Summary Cards Row */
            .summary-cards {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            
            .card {
                background: white;
                border-radius: 16px;
                padding: 24px;
                box-shadow: var(--card-shadow);
                transition: transform 0.2s, box-shadow 0.2s;
            }
            
            .card:hover {
                transform: translateY(-2px);
                box-shadow: var(--card-shadow-hover);
            }
            
            .card-header {
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                margin-bottom: 16px;
            }
            
            .card-title {
                font-size: 0.9em;
                color: var(--gray);
                font-weight: 500;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            
            .card-icon {
                width: 48px;
                height: 48px;
                border-radius: 12px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 1.5em;
            }
            
            .card-icon.primary { background: linear-gradient(135deg, var(--primary), var(--primary-dark)); }
            .card-icon.success { background: linear-gradient(135deg, #28a745, #20c997); }
            .card-icon.warning { background: linear-gradient(135deg, #ffc107, #fd7e14); }
            .card-icon.info { background: linear-gradient(135deg, #17a2b8, #0dcaf0); }
            
            .card-value {
                font-size: 2em;
                font-weight: 700;
                color: var(--dark);
                margin-bottom: 8px;
            }
            
            .card-change {
                display: inline-flex;
                align-items: center;
                gap: 4px;
                padding: 4px 10px;
                border-radius: 20px;
                font-size: 0.85em;
                font-weight: 600;
            }
            
            .card-change.positive {
                background: rgba(40, 167, 69, 0.1);
                color: var(--success);
            }
            
            .card-change.negative {
                background: rgba(220, 53, 69, 0.1);
                color: var(--danger);
            }
            
            /* Charts Grid */
            .charts-grid {
                display: grid;
                grid-template-columns: 2fr 1fr;
                gap: 20px;
                margin-bottom: 30px;
            }
            
            @media (max-width: 1200px) {
                .charts-grid {
                    grid-template-columns: 1fr;
                }
            }
            
            .chart-card {
                background: white;
                border-radius: 16px;
                padding: 24px;
                box-shadow: var(--card-shadow);
            }
            
            .chart-card-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 20px;
            }
            
            .chart-card-title {
                font-size: 1.1em;
                font-weight: 600;
                color: var(--dark);
            }
            
            .period-selector {
                display: flex;
                gap: 8px;
            }
            
            .period-btn {
                padding: 6px 14px;
                border: 1px solid #e0e0e0;
                background: white;
                border-radius: 6px;
                cursor: pointer;
                font-size: 0.85em;
                color: var(--gray);
                transition: all 0.2s;
            }
            
            .period-btn:hover {
                border-color: var(--primary);
                color: var(--primary);
            }
            
            .period-btn.active {
                background: var(--primary);
                border-color: var(--primary);
                color: white;
            }
            
            .chart-container {
                position: relative;
                height: 350px;
            }
            
            /* Allocation Chart */
            .allocation-container {
                display: flex;
                flex-direction: column;
            }
            
            .allocation-legend {
                margin-top: 20px;
            }
            
            .legend-item {
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 10px 0;
                border-bottom: 1px solid #f0f0f0;
            }
            
            .legend-item:last-child {
                border-bottom: none;
            }
            
            .legend-color {
                width: 12px;
                height: 12px;
                border-radius: 3px;
                margin-right: 10px;
            }
            
            .legend-label {
                display: flex;
                align-items: center;
                color: var(--dark);
                font-size: 0.9em;
            }
            
            .legend-value {
                font-weight: 600;
                color: var(--dark);
            }
            
            .legend-percent {
                color: var(--gray);
                font-size: 0.85em;
                margin-left: 8px;
            }
            
            /* Retirement Section */
            .retirement-section {
                margin-bottom: 30px;
            }
            
            .section-title {
                font-size: 1.3em;
                font-weight: 600;
                color: var(--dark);
                margin-bottom: 20px;
            }
            
            .retirement-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
            }
            
            .fire-progress {
                padding: 30px;
            }
            
            .progress-container {
                margin: 20px 0;
            }
            
            .progress-label {
                display: flex;
                justify-content: space-between;
                margin-bottom: 8px;
                font-size: 0.9em;
            }
            
            .progress-bar {
                height: 20px;
                background: #e9ecef;
                border-radius: 10px;
                overflow: hidden;
            }
            
            .progress-fill {
                height: 100%;
                background: linear-gradient(90deg, var(--primary), var(--primary-dark));
                border-radius: 10px;
                transition: width 0.5s ease;
            }
            
            .fire-stats {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 15px;
                margin-top: 20px;
            }
            
            .fire-stat {
                text-align: center;
                padding: 15px;
                background: var(--light);
                border-radius: 10px;
            }
            
            .fire-stat-value {
                font-size: 1.4em;
                font-weight: 700;
                color: var(--primary);
            }
            
            .fire-stat-label {
                font-size: 0.8em;
                color: var(--gray);
                margin-top: 4px;
            }
            
            /* Withdrawal Cards */
            .withdrawal-cards {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 15px;
            }
            
            .withdrawal-card {
                text-align: center;
                padding: 20px;
                background: var(--light);
                border-radius: 12px;
            }
            
            .withdrawal-rate {
                font-size: 1.5em;
                font-weight: 700;
                color: var(--primary);
            }
            
            .withdrawal-amount {
                font-size: 1.1em;
                font-weight: 600;
                color: var(--dark);
                margin: 8px 0;
            }
            
            .withdrawal-monthly {
                font-size: 0.85em;
                color: var(--gray);
            }
            
            /* Data Table */
            .table-section {
                background: white;
                border-radius: 16px;
                padding: 24px;
                box-shadow: var(--card-shadow);
            }
            
            .table-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 20px;
            }
            
            .table-container {
                overflow-x: auto;
            }
            
            table {
                width: 100%;
                border-collapse: collapse;
            }
            
            th {
                text-align: left;
                padding: 12px 16px;
                background: var(--light);
                font-weight: 600;
                font-size: 0.85em;
                color: var(--gray);
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            
            th:first-child { border-radius: 8px 0 0 8px; }
            th:last-child { border-radius: 0 8px 8px 0; }
            
            td {
                padding: 14px 16px;
                border-bottom: 1px solid #f0f0f0;
                font-size: 0.95em;
            }
            
            tr:hover td {
                background: #fafafa;
            }
            
            .amount-positive { color: var(--success); }
            .amount-negative { color: var(--danger); }
            
            /* Loading State */
            .loading {
                display: flex;
                align-items: center;
                justify-content: center;
                height: 200px;
                color: var(--gray);
            }
            
            .spinner {
                width: 40px;
                height: 40px;
                border: 3px solid #f0f0f0;
                border-top-color: var(--primary);
                border-radius: 50%;
                animation: spin 1s linear infinite;
            }
            
            @keyframes spin {
                to { transform: rotate(360deg); }
            }
            
            /* Tab Navigation */
            .tabs {
                display: flex;
                gap: 4px;
                background: #e9ecef;
                padding: 4px;
                border-radius: 10px;
                margin-bottom: 20px;
                width: fit-content;
            }
            
            .tab {
                padding: 10px 24px;
                border: none;
                background: transparent;
                border-radius: 8px;
                cursor: pointer;
                font-weight: 500;
                color: var(--gray);
                transition: all 0.2s;
            }
            
            .tab:hover {
                color: var(--dark);
            }
            
            .tab.active {
                background: white;
                color: var(--primary);
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            
            /* Utilities */
            .text-muted { color: var(--gray); }
            .text-success { color: var(--success); }
            .text-danger { color: var(--danger); }
            .mb-0 { margin-bottom: 0; }
        </style>
    </head>
    <body>
        <div class="app-container">
            <!-- Header -->
            <header class="header">
                <div>
                    <h1>💰 Net Worth Dashboard</h1>
                    <div class="header-subtitle" id="lastUpdated">Loading...</div>
                </div>
                <div class="header-actions">
                    <button class="btn btn-outline" onclick="refreshData()">↻ Refresh</button>
                    <button class="btn btn-primary" onclick="exportData()">📥 Export</button>
                </div>
            </header>
            
            <main class="main-content">
                <!-- Summary Cards -->
                <div class="summary-cards">
                    <div class="card">
                        <div class="card-header">
                            <span class="card-title">Total Net Worth</span>
                            <div class="card-icon primary">💎</div>
                        </div>
                        <div class="card-value" id="netWorthValue">--</div>
                        <span class="card-change positive" id="netWorthChange">--</span>
                    </div>
                    
                    <div class="card">
                        <div class="card-header">
                            <span class="card-title">Investible Assets</span>
                            <div class="card-icon success">📈</div>
                        </div>
                        <div class="card-value" id="investibleValue">--</div>
                        <span class="card-change positive" id="investiblePct">--</span>
                    </div>
                    
                    <div class="card">
                        <div class="card-header">
                            <span class="card-title">YTD Change</span>
                            <div class="card-icon warning">📊</div>
                        </div>
                        <div class="card-value" id="ytdValue">--</div>
                        <span class="card-change positive" id="ytdPct">--</span>
                    </div>
                    
                    <div class="card">
                        <div class="card-header">
                            <span class="card-title">4% Safe Withdrawal</span>
                            <div class="card-icon info">🏦</div>
                        </div>
                        <div class="card-value" id="withdrawalValue">--</div>
                        <span class="text-muted" id="withdrawalMonthly">-- /month</span>
                    </div>
                </div>
                
                <!-- Charts Row -->
                <div class="charts-grid">
                    <!-- Net Worth Chart -->
                    <div class="chart-card">
                        <div class="chart-card-header">
                            <h3 class="chart-card-title">Net Worth Over Time</h3>
                            <div class="period-selector">
                                <button class="period-btn" data-period="1m">1M</button>
                                <button class="period-btn" data-period="3m">3M</button>
                                <button class="period-btn" data-period="6m">6M</button>
                                <button class="period-btn active" data-period="1y">1Y</button>
                                <button class="period-btn" data-period="all">All</button>
                            </div>
                        </div>
                        <div class="chart-container">
                            <canvas id="netWorthChart"></canvas>
                        </div>
                    </div>
                    
                    <!-- Allocation Chart -->
                    <div class="chart-card allocation-container">
                        <h3 class="chart-card-title">Account Allocation</h3>
                        <div class="chart-container" style="height: 250px;">
                            <canvas id="allocationChart"></canvas>
                        </div>
                        <div class="allocation-legend" id="allocationLegend"></div>
                    </div>
                </div>
                
                <!-- Retirement Planning Section -->
                <div class="retirement-section">
                    <h2 class="section-title">🎯 Retirement Planning</h2>
                    <div class="retirement-grid">
                        <!-- FIRE Progress Card -->
                        <div class="card fire-progress">
                            <h3 class="chart-card-title">FIRE Progress</h3>
                            <div class="progress-container">
                                <div class="progress-label">
                                    <span>Progress to 25x expenses</span>
                                    <span id="fireProgressPct">--</span>
                                </div>
                                <div class="progress-bar">
                                    <div class="progress-fill" id="fireProgressBar" style="width: 0%"></div>
                                </div>
                            </div>
                            <div class="fire-stats">
                                <div class="fire-stat">
                                    <div class="fire-stat-value" id="fireNumber">--</div>
                                    <div class="fire-stat-label">FIRE Number (25x)</div>
                                </div>
                                <div class="fire-stat">
                                    <div class="fire-stat-value" id="yearsExpenses">--</div>
                                    <div class="fire-stat-label">Years of Expenses</div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Withdrawal Scenarios -->
                        <div class="card">
                            <h3 class="chart-card-title">Withdrawal Scenarios</h3>
                            <p class="text-muted" style="margin: 10px 0 20px;">Annual safe withdrawal amounts</p>
                            <div class="withdrawal-cards" id="withdrawalCards">
                                <div class="withdrawal-card">
                                    <div class="withdrawal-rate">3%</div>
                                    <div class="withdrawal-amount" id="w3pct">--</div>
                                    <div class="withdrawal-monthly" id="w3pctMonthly">--/mo</div>
                                </div>
                                <div class="withdrawal-card">
                                    <div class="withdrawal-rate">4%</div>
                                    <div class="withdrawal-amount" id="w4pct">--</div>
                                    <div class="withdrawal-monthly" id="w4pctMonthly">--/mo</div>
                                </div>
                                <div class="withdrawal-card">
                                    <div class="withdrawal-rate">5%</div>
                                    <div class="withdrawal-amount" id="w5pct">--</div>
                                    <div class="withdrawal-monthly" id="w5pctMonthly">--/mo</div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Growth Projections Chart -->
                        <div class="card">
                            <h3 class="chart-card-title">10-Year Growth Projection (8%)</h3>
                            <div class="chart-container" style="height: 250px;">
                                <canvas id="projectionChart"></canvas>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Account Trends Chart -->
                <div class="chart-card" style="margin-bottom: 30px;">
                    <div class="chart-card-header">
                        <h3 class="chart-card-title">Account Trends</h3>
                        <div class="period-selector" id="trendsPeriodSelector">
                            <button class="period-btn" data-period="3m">3M</button>
                            <button class="period-btn active" data-period="6m">6M</button>
                            <button class="period-btn" data-period="1y">1Y</button>
                            <button class="period-btn" data-period="all">All</button>
                        </div>
                    </div>
                    <div class="chart-container">
                        <canvas id="trendsChart"></canvas>
                    </div>
                </div>
                
                <!-- Data Table -->
                <div class="table-section">
                    <div class="table-header">
                        <h3 class="chart-card-title">Entry History</h3>
                        <div class="tabs">
                            <button class="tab active" data-view="recent">Recent</button>
                            <button class="tab" data-view="all">All Data</button>
                        </div>
                    </div>
                    <div class="table-container">
                        <table>
                            <thead>
                                <tr>
                                    <th>Date</th>
                                    <th>Net Worth</th>
                                    <th>Change</th>
                                    <th>E*TRADE</th>
                                    <th>Crypto</th>
                                    <th>Fidelity</th>
                                    <th>Capital One</th>
                                    <th>Notes</th>
                                </tr>
                            </thead>
                            <tbody id="dataTableBody">
                                <tr><td colspan="8" class="loading">Loading data...</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </main>
        </div>
        
        <script>
            // Format currency
            const formatCurrency = (value) => {
                if (value === null || value === undefined) return '--';
                const num = parseFloat(value);
                if (isNaN(num)) return '--';
                return new Intl.NumberFormat('en-US', {
                    style: 'currency',
                    currency: 'USD',
                    minimumFractionDigits: 0,
                    maximumFractionDigits: 0
                }).format(num);
            };
            
            const formatPercent = (value) => {
                if (value === null || value === undefined) return '--';
                const num = parseFloat(value);
                if (isNaN(num)) return '--';
                const sign = num >= 0 ? '+' : '';
                return sign + num.toFixed(2) + '%';
            };
            
            const formatDate = (dateStr) => {
                return new Date(dateStr).toLocaleDateString('en-US', {
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric'
                });
            };
            
            // Chart instances
            let netWorthChart, allocationChart, trendsChart, projectionChart;
            let currentPeriod = '1y';
            let trendsPeriod = '6m';
            
            // Initialize
            document.addEventListener('DOMContentLoaded', () => {
                initCharts();
                loadAllData();
                setupEventListeners();
            });
            
            function setupEventListeners() {
                // Period selectors for main chart
                document.querySelectorAll('.period-selector:not(#trendsPeriodSelector) .period-btn').forEach(btn => {
                    btn.addEventListener('click', (e) => {
                        document.querySelectorAll('.period-selector:not(#trendsPeriodSelector) .period-btn').forEach(b => b.classList.remove('active'));
                        e.currentTarget.classList.add('active');
                        currentPeriod = e.currentTarget.dataset.period;
                        loadNetWorthChart();
                    });
                });
                
                // Period selectors for trends chart
                document.querySelectorAll('#trendsPeriodSelector .period-btn').forEach(btn => {
                    btn.addEventListener('click', (e) => {
                        document.querySelectorAll('#trendsPeriodSelector .period-btn').forEach(b => b.classList.remove('active'));
                        e.currentTarget.classList.add('active');
                        trendsPeriod = e.currentTarget.dataset.period;
                        loadTrendsChart();
                    });
                });
                
                // Table view tabs
                document.querySelectorAll('.tab').forEach(tab => {
                    tab.addEventListener('click', (e) => {
                        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                        e.currentTarget.classList.add('active');
                        loadTableData(e.currentTarget.dataset.view);
                    });
                });
            }
            
            function initCharts() {
                // Net Worth Line Chart
                const nwCtx = document.getElementById('netWorthChart').getContext('2d');
                netWorthChart = new Chart(nwCtx, {
                    type: 'line',
                    data: { labels: [], datasets: [] },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { display: false }
                        },
                        scales: {
                            x: {
                                grid: { display: false }
                            },
                            y: {
                                ticks: {
                                    callback: (value) => '$' + (value / 1000).toFixed(0) + 'k'
                                }
                            }
                        },
                        interaction: {
                            intersect: false,
                            mode: 'index'
                        }
                    }
                });
                
                // Allocation Doughnut Chart
                const allocCtx = document.getElementById('allocationChart').getContext('2d');
                allocationChart = new Chart(allocCtx, {
                    type: 'doughnut',
                    data: { labels: [], datasets: [] },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { display: false }
                        },
                        cutout: '65%'
                    }
                });
                
                // Trends Stacked Area Chart
                const trendsCtx = document.getElementById('trendsChart').getContext('2d');
                trendsChart = new Chart(trendsCtx, {
                    type: 'line',
                    data: { labels: [], datasets: [] },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { position: 'top' }
                        },
                        scales: {
                            x: { grid: { display: false }, stacked: true },
                            y: {
                                stacked: true,
                                ticks: {
                                    callback: (value) => '$' + (value / 1000).toFixed(0) + 'k'
                                }
                            }
                        }
                    }
                });
                
                // Projection Chart
                const projCtx = document.getElementById('projectionChart').getContext('2d');
                projectionChart = new Chart(projCtx, {
                    type: 'bar',
                    data: { labels: [], datasets: [] },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { display: false }
                        },
                        scales: {
                            y: {
                                ticks: {
                                    callback: (value) => '$' + (value / 1000000).toFixed(1) + 'M'
                                }
                            }
                        }
                    }
                });
            }
            
            async function loadAllData() {
                await Promise.all([
                    loadSummary(),
                    loadNetWorthChart(),
                    loadAllocation(),
                    loadTrendsChart(),
                    loadRetirement(),
                    loadTableData('recent')
                ]);
            }
            
            async function loadSummary() {
                try {
                    const res = await fetch('/marketapi/v1/networth/summary', { credentials: 'include' });
                    const data = await res.json();
                    
                    if (data.success) {
                        const s = data.summary;
                        document.getElementById('netWorthValue').textContent = formatCurrency(s.latest.net_worth);
                        document.getElementById('investibleValue').textContent = formatCurrency(s.latest.investible_assets);
                        document.getElementById('ytdValue').textContent = formatCurrency(s.ytd.change_dollars);
                        document.getElementById('withdrawalValue').textContent = formatCurrency(s.withdrawals.four_percent);
                        
                        // Set change indicators
                        const ytdPct = parseFloat(s.ytd.change_percent);
                        const ytdEl = document.getElementById('ytdPct');
                        ytdEl.textContent = formatPercent(ytdPct);
                        ytdEl.className = 'card-change ' + (ytdPct >= 0 ? 'positive' : 'negative');
                        
                        const nwChangeEl = document.getElementById('netWorthChange');
                        nwChangeEl.textContent = formatPercent(ytdPct) + ' YTD';
                        nwChangeEl.className = 'card-change ' + (ytdPct >= 0 ? 'positive' : 'negative');
                        
                        // Monthly withdrawal
                        const monthly = parseFloat(s.withdrawals.four_percent) / 12;
                        document.getElementById('withdrawalMonthly').textContent = formatCurrency(monthly) + ' /month';
                        
                        // Investible percentage of net worth
                        const invPct = (parseFloat(s.latest.investible_assets) / parseFloat(s.latest.net_worth) * 100).toFixed(1);
                        document.getElementById('investiblePct').textContent = invPct + '% of NW';
                        document.getElementById('investiblePct').className = 'card-change positive';
                        
                        // Last updated
                        document.getElementById('lastUpdated').textContent = 'Last entry: ' + formatDate(s.latest.date);
                    }
                } catch (err) {
                    console.error('Failed to load summary:', err);
                }
            }
            
            async function loadNetWorthChart() {
                try {
                    const res = await fetch(`/marketapi/v1/networth/chart/timeseries?period=${currentPeriod}&metrics=net_worth,investible_assets`, { credentials: 'include' });
                    const data = await res.json();
                    
                    if (data.success) {
                        netWorthChart.data.labels = data.labels.map(d => formatDate(d));
                        netWorthChart.data.datasets = [
                            {
                                label: 'Net Worth',
                                data: data.datasets.net_worth.data,
                                borderColor: '#667eea',
                                backgroundColor: 'rgba(102, 126, 234, 0.1)',
                                fill: true,
                                tension: 0.3
                            },
                            {
                                label: 'Investible',
                                data: data.datasets.investible_assets?.data || [],
                                borderColor: '#28a745',
                                backgroundColor: 'transparent',
                                borderDash: [5, 5],
                                tension: 0.3
                            }
                        ];
                        netWorthChart.update();
                    }
                } catch (err) {
                    console.error('Failed to load net worth chart:', err);
                }
            }
            
            async function loadAllocation() {
                try {
                    const res = await fetch('/marketapi/v1/networth/chart/allocation', { credentials: 'include' });
                    const data = await res.json();
                    
                    if (data.success) {
                        allocationChart.data.labels = data.labels;
                        allocationChart.data.datasets = [{
                            data: data.data,
                            backgroundColor: data.colors,
                            borderWidth: 0
                        }];
                        allocationChart.update();
                        
                        // Build legend
                        const legend = document.getElementById('allocationLegend');
                        legend.innerHTML = data.allocation.slice(0, 6).map(a => `
                            <div class="legend-item">
                                <span class="legend-label">
                                    <span class="legend-color" style="background: ${a.color}"></span>
                                    ${a.account}
                                </span>
                                <span>
                                    <span class="legend-value">${formatCurrency(a.value)}</span>
                                    <span class="legend-percent">${a.percentage}%</span>
                                </span>
                            </div>
                        `).join('');
                    }
                } catch (err) {
                    console.error('Failed to load allocation:', err);
                }
            }
            
            async function loadTrendsChart() {
                try {
                    const res = await fetch(`/marketapi/v1/networth/chart/trends?period=${trendsPeriod}`, { credentials: 'include' });
                    const data = await res.json();
                    
                    if (data.success) {
                        trendsChart.data.labels = data.labels.map(d => formatDate(d));
                        trendsChart.data.datasets = data.datasets;
                        trendsChart.update();
                    }
                } catch (err) {
                    console.error('Failed to load trends:', err);
                }
            }
            
            async function loadRetirement() {
                try {
                    const res = await fetch('/marketapi/v1/networth/retirement', { credentials: 'include' });
                    const data = await res.json();
                    
                    if (data.success) {
                        const f = data.fire;
                        const w = data.withdrawals;
                        
                        // FIRE progress
                        const progress = Math.min(f.progress_25x_percent || 0, 100);
                        document.getElementById('fireProgressPct').textContent = progress.toFixed(1) + '%';
                        document.getElementById('fireProgressBar').style.width = progress + '%';
                        document.getElementById('fireNumber').textContent = formatCurrency(f.number_25x);
                        document.getElementById('yearsExpenses').textContent = f.years_of_expenses ? f.years_of_expenses + ' yrs' : '--';
                        
                        // Withdrawal amounts
                        document.getElementById('w3pct').textContent = formatCurrency(w.conservative_3pct.annual);
                        document.getElementById('w3pctMonthly').textContent = formatCurrency(w.conservative_3pct.monthly) + '/mo';
                        document.getElementById('w4pct').textContent = formatCurrency(w.standard_4pct.annual);
                        document.getElementById('w4pctMonthly').textContent = formatCurrency(w.standard_4pct.monthly) + '/mo';
                        document.getElementById('w5pct').textContent = formatCurrency(w.aggressive_5pct.annual);
                        document.getElementById('w5pctMonthly').textContent = formatCurrency(w.aggressive_5pct.monthly) + '/mo';
                        
                        // Projection chart
                        const projections = data.projections_8pct;
                        projectionChart.data.labels = projections.map(p => 'Year ' + p.year);
                        projectionChart.data.datasets = [{
                            label: 'Projected Value',
                            data: projections.map(p => p.projected_value),
                            backgroundColor: 'rgba(102, 126, 234, 0.7)',
                            borderRadius: 6
                        }];
                        projectionChart.update();
                    }
                } catch (err) {
                    console.error('Failed to load retirement data:', err);
                }
            }
            
            async function loadTableData(view) {
                try {
                    const limit = view === 'recent' ? '&limit=20' : '';
                    const res = await fetch(`/marketapi/v1/networth?${limit}`, { credentials: 'include' });
                    const data = await res.json();
                    
                    if (data.success) {
                        let entries = data.data;
                        if (view === 'recent') entries = entries.slice(-20);
                        entries = entries.reverse(); // Most recent first
                        
                        const tbody = document.getElementById('dataTableBody');
                        tbody.innerHTML = entries.map(e => {
                            const change = parseFloat(e.net_worth_change);
                            const changeClass = change >= 0 ? 'amount-positive' : 'amount-negative';
                            const changeSign = change >= 0 ? '+' : '';
                            return `
                                <tr>
                                    <td>${formatDate(e.date)}</td>
                                    <td><strong>${formatCurrency(e.net_worth)}</strong></td>
                                    <td class="${changeClass}">${changeSign}${formatCurrency(change)}</td>
                                    <td>${formatCurrency(e.etrade)}</td>
                                    <td>${formatCurrency(e.crypto)}</td>
                                    <td>${formatCurrency(e.fidelity)}</td>
                                    <td>${formatCurrency(e.capital_one)}</td>
                                    <td class="text-muted">${e.notes || '-'}</td>
                                </tr>
                            `;
                        }).join('');
                    }
                } catch (err) {
                    console.error('Failed to load table data:', err);
                    document.getElementById('dataTableBody').innerHTML = '<tr><td colspan="8">Failed to load data</td></tr>';
                }
            }
            
            function refreshData() {
                loadAllData();
            }
            
            function exportData() {
                window.open('/marketapi/v1/networth', '_blank');
            }
        </script>
    </body>
    </html>
    """


