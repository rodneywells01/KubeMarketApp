from flask import Flask, jsonify, request
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)


# ============================================================================
# Net Worth API Endpoints
# ============================================================================

@app.route("/marketapi/v1/networth", methods=["GET"])
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


# ============================================================================
# Landing Page
# ============================================================================

@app.route("/")
@app.route("/marketapi")
def landing_page():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Market Analysis Dashboard</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }

            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                padding: 20px;
            }

            .container {
                background: white;
                border-radius: 20px;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                padding: 60px;
                max-width: 800px;
                width: 100%;
                text-align: center;
            }

            h1 {
                color: #333;
                font-size: 3em;
                margin-bottom: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }

            .subtitle {
                color: #666;
                font-size: 1.3em;
                margin-bottom: 40px;
            }

            .features {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 30px;
                margin-top: 50px;
            }

            .feature-card {
                background: #f8f9fa;
                padding: 30px 20px;
                border-radius: 15px;
                transition: transform 0.3s ease, box-shadow 0.3s ease;
            }

            .feature-card:hover {
                transform: translateY(-5px);
                box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15);
            }

            .feature-icon {
                font-size: 3em;
                margin-bottom: 15px;
            }

            .feature-title {
                color: #333;
                font-size: 1.2em;
                font-weight: 600;
                margin-bottom: 10px;
            }

            .feature-description {
                color: #666;
                font-size: 0.9em;
                line-height: 1.6;
            }

            .cta-button {
                display: inline-block;
                margin-top: 40px;
                padding: 15px 40px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                text-decoration: none;
                border-radius: 30px;
                font-size: 1.1em;
                font-weight: 600;
                transition: transform 0.3s ease, box-shadow 0.3s ease;
            }

            .cta-button:hover {
                transform: scale(1.05);
                box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4);
            }

            .status {
                margin-top: 30px;
                padding: 15px;
                background: #d4edda;
                color: #155724;
                border-radius: 10px;
                font-weight: 500;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Market Analysis Platform</h1>
            <p class="subtitle">Powerful insights for data-driven decisions</p>

            <div class="status">
                ✓ System Online & Ready
            </div>

            <div class="features">
                <div class="feature-card">
                    <div class="feature-icon">📊</div>
                    <div class="feature-title">Analytics</div>
                    <div class="feature-description">
                        Real-time market analysis and trend visualization
                    </div>
                </div>

                <div class="feature-card">
                    <div class="feature-icon">📈</div>
                    <div class="feature-title">Reports</div>
                    <div class="feature-description">
                        Comprehensive reporting and data exports
                    </div>
                </div>

                <div class="feature-card">
                    <div class="feature-icon">🔍</div>
                    <div class="feature-title">Research</div>
                    <div class="feature-description">
                        Deep dive into market patterns and insights
                    </div>
                </div>
            </div>

            <a href="#" class="cta-button">Get Started</a>
        </div>
    </body>
    </html>
    """

