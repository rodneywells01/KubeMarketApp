"""
Configuration management for MarketApp.

Environment Variables:
    GOOGLE_SERVICE_ACCOUNT_JSON: JSON string containing service account credentials
    GOOGLE_SERVICE_ACCOUNT_FILE: Path to service account JSON file
    GOOGLE_SHEETS_SPREADSHEET_ID: Override default spreadsheet ID
    GOOGLE_SHEETS_SHEET_NAME: Override default sheet name
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class GoogleSheetsConfig:
    """Configuration for Google Sheets integration."""
    spreadsheet_id: str = "1lay4YEVMV6JDlP5rzdS8iegAFxpyoZakb502o7ZtqpA"
    sheet_name: str = "Net Worth Tracking"
    credentials_json: Optional[str] = None
    credentials_file: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> "GoogleSheetsConfig":
        """Load configuration from environment variables."""
        return cls(
            spreadsheet_id=os.environ.get(
                "GOOGLE_SHEETS_SPREADSHEET_ID",
                "1lay4YEVMV6JDlP5rzdS8iegAFxpyoZakb502o7ZtqpA"
            ),
            sheet_name=os.environ.get(
                "GOOGLE_SHEETS_SHEET_NAME",
                "Net Worth Tracking"
            ),
            credentials_json=os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON"),
            credentials_file=os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE"),
        )
    
    def is_configured(self) -> bool:
        """Check if Google Sheets credentials are configured."""
        return bool(self.credentials_json or self.credentials_file)


@dataclass
class AuthConfig:
    """Configuration for API authentication."""
    username: Optional[str] = None
    password: Optional[str] = None
    password_hash: Optional[str] = None
    
    auth: AuthConfig = None
    
    def __post_init__(self):
        if self.google_sheets is None:
            self.google_sheets = GoogleSheetsConfig.from_env()
        if self.auth is None:
            self.auth = AuthConfig.from_env()
    
    @classmethod
    def from_env(cls) -> "AppConfig":
        """Load configuration from environment variables."""
        return cls(
            debug=os.environ.get("FLASK_DEBUG", "").lower() in ("1", "true"),
            host=os.environ.get("HOST", "0.0.0.0"),
            port=int(os.environ.get("PORT", "5000")),
            google_sheets=GoogleSheetsConfig.from_env(),
            auth=Auth

@dataclass
class AppConfig:
    """Main application configuration."""
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 5000
    google_sheets: GoogleSheetsConfig = None
    
    def __post_init__(self):
        if self.google_sheets is None:
            self.google_sheets = GoogleSheetsConfig.from_env()
    
    @classmethod
    def from_env(cls) -> "AppConfig":
        """Load configuration from environment variables."""
        return cls(
            debug=os.environ.get("FLASK_DEBUG", "").lower() in ("1", "true"),
            host=os.environ.get("HOST", "0.0.0.0"),
            port=int(os.environ.get("PORT", "5000")),
            google_sheets=GoogleSheetsConfig.from_env(),
        )


# Global config instance
config = AppConfig.from_env()
