from flask import Flask

app = Flask(__name__)

@app.route("/")
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

