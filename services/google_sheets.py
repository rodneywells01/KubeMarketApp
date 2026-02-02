"""
Google Sheets Data Ingestion Service

This module provides functionality to read data from Google Sheets.
Supports two authentication methods:
1. Service Account (for server-side access) - recommended for production
2. API Key (for public sheets only)

For private sheets, you'll need to set up a Google Cloud Service Account:
1. Go to Google Cloud Console -> APIs & Services -> Credentials
2. Create a Service Account and download the JSON key
3. Share your Google Sheet with the service account email
4. Set GOOGLE_SERVICE_ACCOUNT_JSON environment variable with the JSON content
   or GOOGLE_SERVICE_ACCOUNT_FILE with path to the JSON file
"""

import os
import json
import logging
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from typing import Optional, List, Any

from models.net_worth import NetWorthEntry, NetWorthDataset, COLUMN_MAPPING

logger = logging.getLogger(__name__)


class GoogleSheetsError(Exception):
    """Custom exception for Google Sheets related errors."""
    pass


class GoogleSheetsService:
    """
    Service for reading data from Google Sheets.
    
    Attributes:
        spreadsheet_id: The ID of the Google Spreadsheet
        credentials: Google API credentials object
    """
    
    # Your spreadsheet configuration
    DEFAULT_SPREADSHEET_ID = "1lay4YEVMV6JDlP5rzdS8iegAFxpyoZakb502o7ZtqpA"
    DEFAULT_SHEET_NAME = "(NEW) Net Worth Tracking"  # The actual sheet name
    DEFAULT_SHEET_GID = "35331791"
    
    def __init__(self, spreadsheet_id: Optional[str] = None):
        """
        Initialize the Google Sheets service.
        
        Args:
            spreadsheet_id: Optional spreadsheet ID. Uses default if not provided.
        """
        self.spreadsheet_id = spreadsheet_id or self.DEFAULT_SPREADSHEET_ID
        self._service = None
        self._credentials = None
    
    def _get_credentials(self):
        """Get Google API credentials from environment."""
        if self._credentials:
            return self._credentials
        
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
        except ImportError:
            raise GoogleSheetsError(
                "Google API libraries not installed. Run: "
                "pip install google-api-python-client google-auth"
            )
        
        # Try to get credentials from environment
        creds_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
        creds_file = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE")
        
        if creds_json:
            # Credentials provided as JSON string
            try:
                creds_info = json.loads(creds_json)
                self._credentials = service_account.Credentials.from_service_account_info(
                    creds_info,
                    scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
                )
            except json.JSONDecodeError as e:
                raise GoogleSheetsError(f"Invalid JSON in GOOGLE_SERVICE_ACCOUNT_JSON: {e}")
        elif creds_file:
            # Credentials provided as file path
            if not os.path.exists(creds_file):
                raise GoogleSheetsError(f"Credentials file not found: {creds_file}")
            self._credentials = service_account.Credentials.from_service_account_file(
                creds_file,
                scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
            )
        else:
            # Fallback: check for local credentials.json file
            local_creds_paths = [
                "credentials.json",
                os.path.join(os.path.dirname(os.path.dirname(__file__)), "credentials.json"),
            ]
            for local_path in local_creds_paths:
                if os.path.exists(local_path):
                    logger.info(f"Using local credentials file: {local_path}")
                    self._credentials = service_account.Credentials.from_service_account_file(
                        local_path,
                        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
                    )
                    return self._credentials
            
            raise GoogleSheetsError(
                "No Google credentials found. Set either:\n"
                "  - GOOGLE_SERVICE_ACCOUNT_JSON (JSON string)\n"
                "  - GOOGLE_SERVICE_ACCOUNT_FILE (path to JSON file)\n"
                "  - Or place credentials.json in the project root"
            )
        
        return self._credentials
    
    def _get_service(self):
        """Get or create the Google Sheets API service."""
        if self._service:
            return self._service
        
        try:
            from googleapiclient.discovery import build
        except ImportError:
            raise GoogleSheetsError(
                "Google API libraries not installed. Run: "
                "pip install google-api-python-client google-auth"
            )
        
        credentials = self._get_credentials()
        self._service = build("sheets", "v4", credentials=credentials)
        return self._service
    
    def _parse_date(self, value: Any) -> Optional[date]:
        """Parse a date value from the spreadsheet."""
        if not value:
            return None
        
        if isinstance(value, date):
            return value
        
        value_str = str(value).strip()
        if not value_str:
            return None
        
        # Try common date formats
        formats = [
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%m/%d/%y",
            "%d/%m/%Y",
            "%Y/%m/%d",
            "%B %d, %Y",
            "%b %d, %Y",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(value_str, fmt).date()
            except ValueError:
                continue
        
        # Try parsing as a serial date (Excel/Sheets format)
        try:
            serial = float(value_str)
            # Google Sheets uses December 30, 1899 as day 0
            from datetime import timedelta
            base_date = date(1899, 12, 30)
            return base_date + timedelta(days=int(serial))
        except (ValueError, OverflowError):
            pass
        
        logger.warning(f"Could not parse date: {value_str}")
        return None
    
    def _parse_decimal(self, value: Any) -> Optional[Decimal]:
        """Parse a decimal value from the spreadsheet."""
        if value is None or value == "":
            return None
        
        value_str = str(value).strip()
        if not value_str or value_str.lower() in ("n/a", "-", "—", ""):
            return None
        
        # Remove currency symbols and commas
        cleaned = value_str.replace("$", "").replace(",", "").replace(" ", "")
        
        # Handle percentages
        if cleaned.endswith("%"):
            cleaned = cleaned[:-1]
            try:
                return Decimal(cleaned) / 100
            except InvalidOperation:
                pass
        
        # Handle parentheses for negative numbers
        if cleaned.startswith("(") and cleaned.endswith(")"):
            cleaned = "-" + cleaned[1:-1]
        
        try:
            return Decimal(cleaned)
        except InvalidOperation:
            logger.warning(f"Could not parse decimal: {value_str}")
            return None
    
    def _parse_int(self, value: Any) -> Optional[int]:
        """Parse an integer value from the spreadsheet."""
        if value is None or value == "":
            return None
        
        try:
            return int(float(str(value).strip()))
        except (ValueError, TypeError):
            return None
    
    def read_sheet(
        self,
        sheet_name: Optional[str] = None,
        range_notation: Optional[str] = None
    ) -> List[List[Any]]:
        """
        Read raw data from a Google Sheet.
        
        Args:
            sheet_name: Name of the sheet tab (uses default if not provided)
            range_notation: A1 notation for the range (e.g., "A1:Z100")
        
        Returns:
            List of rows, where each row is a list of cell values
        """
        service = self._get_service()
        
        sheet_name = sheet_name or self.DEFAULT_SHEET_NAME
        
        if range_notation:
            full_range = f"'{sheet_name}'!{range_notation}"
        else:
            full_range = f"'{sheet_name}'"
        
        try:
            result = service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=full_range,
                valueRenderOption="UNFORMATTED_VALUE",
                dateTimeRenderOption="SERIAL_NUMBER"
            ).execute()
            
            return result.get("values", [])
        except Exception as e:
            raise GoogleSheetsError(f"Failed to read sheet: {e}")
    
    def load_net_worth_data(
        self,
        sheet_name: Optional[str] = None
    ) -> NetWorthDataset:
        """
        Load net worth tracking data from the Google Sheet.
        
        Args:
            sheet_name: Name of the sheet tab containing net worth data
        
        Returns:
            NetWorthDataset with all entries from the sheet
        """
        rows = self.read_sheet(sheet_name=sheet_name)
        
        if not rows:
            raise GoogleSheetsError("Sheet is empty")
        
        # First row is headers
        headers = [str(h).strip() for h in rows[0]]
        
        # Map headers to column indices
        header_to_index = {h: i for i, h in enumerate(headers)}
        
        # Build reverse mapping: attribute name -> column index
        attr_to_index = {}
        for sheet_col, attr_name in COLUMN_MAPPING.items():
            if sheet_col in header_to_index:
                attr_to_index[attr_name] = header_to_index[sheet_col]
        
        entries = []
        
        # Process data rows (skip header)
        for row_num, row in enumerate(rows[1:], start=2):
            # Skip empty rows
            if not row or all(cell == "" or cell is None for cell in row):
                continue
            
            # Get date first - skip rows without valid dates
            date_idx = attr_to_index.get("date")
            if date_idx is None or date_idx >= len(row):
                continue
            
            entry_date = self._parse_date(row[date_idx])
            if not entry_date:
                logger.debug(f"Skipping row {row_num}: no valid date")
                continue
            
            # Build entry kwargs
            entry_kwargs = {"date": entry_date}
            
            for attr_name, col_idx in attr_to_index.items():
                if attr_name == "date":
                    continue
                
                if col_idx >= len(row):
                    continue
                
                value = row[col_idx]
                
                # Determine the type based on attribute name
                if attr_name == "notes":
                    entry_kwargs[attr_name] = str(value) if value else None
                elif attr_name == "days_since_last":
                    entry_kwargs[attr_name] = self._parse_int(value)
                else:
                    # All other fields are decimals
                    entry_kwargs[attr_name] = self._parse_decimal(value)
            
            try:
                entry = NetWorthEntry(**entry_kwargs)
                entries.append(entry)
            except Exception as e:
                logger.warning(f"Failed to create entry for row {row_num}: {e}")
        
        dataset = NetWorthDataset(
            entries=entries,
            source_sheet_id=self.spreadsheet_id,
            source_sheet_name=sheet_name or self.DEFAULT_SHEET_NAME,
            last_updated=datetime.now()
        )
        
        logger.info(f"Loaded {len(entries)} net worth entries from Google Sheets")
        
        return dataset


# Convenience function for quick access
def load_net_worth_from_sheets(
    spreadsheet_id: Optional[str] = None,
    sheet_name: Optional[str] = None
) -> NetWorthDataset:
    """
    Convenience function to load net worth data from Google Sheets.
    
    Args:
        spreadsheet_id: Optional spreadsheet ID (uses default if not provided)
        sheet_name: Optional sheet name (uses default if not provided)
    
    Returns:
        NetWorthDataset with all entries
    """
    service = GoogleSheetsService(spreadsheet_id=spreadsheet_id)
    return service.load_net_worth_data(sheet_name=sheet_name)
