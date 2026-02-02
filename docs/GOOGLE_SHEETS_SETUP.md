# Google Sheets Integration Setup

This guide explains how to set up Google Sheets integration for importing net worth tracking data.

## Quick Start

### 1. Create a Google Cloud Service Account

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the **Google Sheets API**:
   - Go to "APIs & Services" → "Library"
   - Search for "Google Sheets API"
   - Click "Enable"

4. Create a Service Account:
   - Go to "APIs & Services" → "Credentials"
   - Click "Create Credentials" → "Service Account"
   - Give it a name (e.g., "marketapp-sheets-reader")
   - Click "Create and Continue"
   - Skip the optional steps and click "Done"

5. Create a JSON Key:
   - Click on the newly created service account
   - Go to "Keys" tab
   - Click "Add Key" → "Create new key"
   - Select "JSON" and click "Create"
   - Save the downloaded JSON file securely

### 2. Share Your Google Sheet

1. Open your Google Sheet
2. Click "Share" button
3. Add the service account email (found in the JSON file as `client_email`)
   - Example: `marketapp-sheets-reader@your-project.iam.gserviceaccount.com`
4. Give it "Viewer" access (read-only is sufficient)

### 3. Configure the Application

#### Option A: Environment Variable (Recommended for Production)

```bash
# Set the JSON content directly
export GOOGLE_SERVICE_ACCOUNT_JSON='{"type": "service_account", "project_id": "...", ...}'

# Or set the path to the JSON file
export GOOGLE_SERVICE_ACCOUNT_FILE=/path/to/service-account.json
```

#### Option B: Kubernetes Secret

```bash
# Create the secret from the JSON file
kubectl create secret generic google-sheets-credentials \
  --from-file=credentials.json=/path/to/service-account.json \
  -n kube-market-app
```

Then update your Helm values to mount the secret:

```yaml
# In mychart/values.yaml or a separate values file
extraEnv:
  - name: GOOGLE_SERVICE_ACCOUNT_FILE
    value: /secrets/google/credentials.json

extraVolumes:
  - name: google-credentials
    secret:
      secretName: google-sheets-credentials

extraVolumeMounts:
  - name: google-credentials
    mountPath: /secrets/google
    readOnly: true
```

## API Endpoints

Once configured, the following endpoints are available:

### Get All Net Worth Data
```
GET /marketapi/v1/networth
```

Query parameters:
- `start_date` (optional): Filter from this date (YYYY-MM-DD)
- `end_date` (optional): Filter until this date (YYYY-MM-DD)
- `latest` (optional): Set to "true" to get only the most recent entry

### Get Net Worth Summary
```
GET /marketapi/v1/networth/summary
```

Returns summary statistics including:
- Latest net worth and account balances
- YTD change (dollars and percentage)
- Withdrawal calculations (3% and 4%)
- Growth projections

## Testing Locally

```bash
# Install dependencies
cd KubeMarketApp
pip install -e .

# Set credentials
export GOOGLE_SERVICE_ACCOUNT_FILE=/path/to/credentials.json

# Run the app
flask run --host=0.0.0.0 --port=5000

# Test the endpoint
curl http://localhost:5000/marketapi/v1/networth/summary
```

## Data Schema

The following columns are imported from your Google Sheet:

| Column | Field | Type |
|--------|-------|------|
| Date | date | date |
| E*TRADE | etrade | decimal |
| Crypto | crypto | decimal |
| NFTs | nfts | decimal |
| Capital One | capital_one | decimal |
| thinkorswim | thinkorswim | decimal |
| TradeStation | tradestation | decimal |
| Fidelity | fidelity | decimal |
| Car | car | decimal |
| Misc | misc | decimal |
| Tax Correction | tax_correction | decimal |
| Inheritance | inheritance | decimal |
| Semi-Liquid Assets | semi_liquid_assets | decimal |
| Investible Assets | investible_assets | decimal |
| Net Worth | net_worth | decimal |
| Net Worth Change | net_worth_change | decimal |
| Days Since Last | days_since_last | integer |
| Daily Net Worth Change | daily_net_worth_change | decimal |
| $ YTD Change | ytd_change_dollars | decimal |
| % YTD Change | ytd_change_percent | decimal |
| 3% Withdrawl | withdrawal_3_percent | decimal |
| 4% Withdrawl | withdrawal_4_percent | decimal |
| 8% Growth | growth_8_percent | decimal |
| Living Expenses | living_expenses | decimal |
| Retirement Spending | retirement_spending | decimal |
| COF Comp | cof_comp | decimal |
| Notes | notes | string |

## Troubleshooting

### "Google Sheets dependencies not installed"
```bash
pip install google-api-python-client google-auth
```

### "No Google credentials found"
Make sure either `GOOGLE_SERVICE_ACCOUNT_JSON` or `GOOGLE_SERVICE_ACCOUNT_FILE` is set.

### "Permission denied" or "Forbidden"
1. Verify the Google Sheets API is enabled in your Google Cloud project
2. Make sure you shared the spreadsheet with the service account email
3. Check that the service account has at least "Viewer" access

### "Sheet not found"
Verify the sheet name matches exactly (including case and spaces). Default is "Net Worth Tracking".
