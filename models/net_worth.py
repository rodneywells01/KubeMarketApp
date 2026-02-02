"""
Net Worth Tracking Data Model

This module defines the schema for net worth tracking data imported from Google Sheets.
Schema is based on the actual columns in the user's net worth tracking spreadsheet.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List


@dataclass
class NetWorthEntry:
    """
    A single net worth snapshot entry - one row from the Google Sheet.
    
    Account Balances (Assets):
        - etrade: E*TRADE brokerage account
        - crypto: Cryptocurrency holdings
        - nfts: NFT holdings
        - capital_one: Capital One bank account
        - thinkorswim: thinkorswim (TD Ameritrade) brokerage
        - tradestation: TradeStation brokerage
        - fidelity: Fidelity account (retirement/brokerage)
        - car: Vehicle asset value
        - misc: Miscellaneous assets
        - tax_correction: Tax-related adjustments
        - inheritance: Inheritance funds
    
    Calculated Fields:
        - semi_liquid_assets: Subtotal of semi-liquid assets
        - investible_assets: Subtotal of investible assets
        - net_worth: Total net worth
        - net_worth_change: Change since last entry
        - days_since_last: Days since previous entry
        - daily_net_worth_change: Daily rate of change
        - ytd_change_dollars: Year-to-date change in dollars
        - ytd_change_percent: Year-to-date change as percentage
        - withdrawal_3_percent: 3% withdrawal amount (safe withdrawal)
        - withdrawal_4_percent: 4% withdrawal amount (standard withdrawal)
        - growth_8_percent: 8% growth projection
        - living_expenses: Monthly/annual living expenses
        - retirement_spending: Retirement spending budget
        - cof_comp: Capital One comparison metric
        - notes: Freeform notes
    """
    # Primary key
    date: date
    
    # Account balances (assets)
    etrade: Optional[Decimal] = None
    crypto: Optional[Decimal] = None
    nfts: Optional[Decimal] = None
    capital_one: Optional[Decimal] = None
    thinkorswim: Optional[Decimal] = None
    tradestation: Optional[Decimal] = None
    fidelity: Optional[Decimal] = None
    car: Optional[Decimal] = None
    misc: Optional[Decimal] = None
    tax_correction: Optional[Decimal] = None
    inheritance: Optional[Decimal] = None
    
    # Calculated/summary fields
    semi_liquid_assets: Optional[Decimal] = None
    investible_assets: Optional[Decimal] = None
    net_worth: Optional[Decimal] = None
    net_worth_change: Optional[Decimal] = None
    days_since_last: Optional[int] = None
    daily_net_worth_change: Optional[Decimal] = None
    ytd_change_dollars: Optional[Decimal] = None
    ytd_change_percent: Optional[Decimal] = None
    withdrawal_3_percent: Optional[Decimal] = None
    withdrawal_4_percent: Optional[Decimal] = None
    growth_8_percent: Optional[Decimal] = None
    living_expenses: Optional[Decimal] = None
    retirement_spending: Optional[Decimal] = None
    cof_comp: Optional[Decimal] = None
    notes: Optional[str] = None
    
    def get_account_balances(self) -> dict[str, Decimal]:
        """Get all account balances as a dictionary."""
        accounts = {
            "E*TRADE": self.etrade,
            "Crypto": self.crypto,
            "NFTs": self.nfts,
            "Capital One": self.capital_one,
            "thinkorswim": self.thinkorswim,
            "TradeStation": self.tradestation,
            "Fidelity": self.fidelity,
            "Car": self.car,
            "Misc": self.misc,
            "Tax Correction": self.tax_correction,
            "Inheritance": self.inheritance,
        }
        return {k: v for k, v in accounts.items() if v is not None}
    
    def to_dict(self) -> dict:
        """Convert entry to dictionary for JSON serialization."""
        def decimal_to_str(val):
            return str(val) if val is not None else None
        
        return {
            "date": self.date.isoformat(),
            # Account balances
            "etrade": decimal_to_str(self.etrade),
            "crypto": decimal_to_str(self.crypto),
            "nfts": decimal_to_str(self.nfts),
            "capital_one": decimal_to_str(self.capital_one),
            "thinkorswim": decimal_to_str(self.thinkorswim),
            "tradestation": decimal_to_str(self.tradestation),
            "fidelity": decimal_to_str(self.fidelity),
            "car": decimal_to_str(self.car),
            "misc": decimal_to_str(self.misc),
            "tax_correction": decimal_to_str(self.tax_correction),
            "inheritance": decimal_to_str(self.inheritance),
            # Calculated fields
            "semi_liquid_assets": decimal_to_str(self.semi_liquid_assets),
            "investible_assets": decimal_to_str(self.investible_assets),
            "net_worth": decimal_to_str(self.net_worth),
            "net_worth_change": decimal_to_str(self.net_worth_change),
            "days_since_last": self.days_since_last,
            "daily_net_worth_change": decimal_to_str(self.daily_net_worth_change),
            "ytd_change_dollars": decimal_to_str(self.ytd_change_dollars),
            "ytd_change_percent": decimal_to_str(self.ytd_change_percent),
            "withdrawal_3_percent": decimal_to_str(self.withdrawal_3_percent),
            "withdrawal_4_percent": decimal_to_str(self.withdrawal_4_percent),
            "growth_8_percent": decimal_to_str(self.growth_8_percent),
            "living_expenses": decimal_to_str(self.living_expenses),
            "retirement_spending": decimal_to_str(self.retirement_spending),
            "cof_comp": decimal_to_str(self.cof_comp),
            "notes": self.notes,
        }


# Column mapping from Google Sheet headers to NetWorthEntry attributes
COLUMN_MAPPING = {
    "Date": "date",
    "E*TRADE": "etrade",
    "Crypto": "crypto",
    "NFTs": "nfts",
    "Capital One": "capital_one",
    "thinkorswim": "thinkorswim",
    "TradeStation": "tradestation",
    "Fidelity": "fidelity",
    "Car": "car",
    "Misc": "misc",
    "Tax Correction": "tax_correction",
    "Inheritance": "inheritance",
    "Semi-Liquid Assets": "semi_liquid_assets",
    "Investible Assets": "investible_assets",
    "Net Worth": "net_worth",
    "Net Worth Change": "net_worth_change",
    "Days Since Last": "days_since_last",
    "Daily Net Worth Change": "daily_net_worth_change",
    "$ YTD Change": "ytd_change_dollars",
    "% YTD Change": "ytd_change_percent",
    "3% Withdrawl": "withdrawal_3_percent",  # Note: typo in original sheet
    "4% Withdrawl": "withdrawal_4_percent",  # Note: typo in original sheet
    "8% Growth": "growth_8_percent",
    "Living Expenses": "living_expenses",
    "Retirement Spending": "retirement_spending",
    "COF Comp": "cof_comp",
    "Notes": "notes",
}


@dataclass
class NetWorthDataset:
    """
    Complete net worth tracking dataset from Google Sheets.
    
    Contains the time series of net worth entries and metadata about the source.
    """
    entries: List[NetWorthEntry] = field(default_factory=list)
    source_sheet_id: Optional[str] = None
    source_sheet_name: Optional[str] = None
    last_updated: Optional[datetime] = None
    
    def get_latest_entry(self) -> Optional[NetWorthEntry]:
        """Get the most recent net worth entry."""
        if not self.entries:
            return None
        return max(self.entries, key=lambda e: e.date)
    
    def get_entry_by_date(self, target_date: date) -> Optional[NetWorthEntry]:
        """Get net worth entry for a specific date."""
        for entry in self.entries:
            if entry.date == target_date:
                return entry
        return None
    
    def get_entries_in_range(self, start_date: date, end_date: date) -> List[NetWorthEntry]:
        """Get all entries within a date range (inclusive)."""
        return sorted(
            [entry for entry in self.entries if start_date <= entry.date <= end_date],
            key=lambda e: e.date
        )
    
    def get_net_worth_series(self) -> List[tuple[date, Decimal]]:
        """Get time series of (date, net_worth) tuples for charting."""
        return [
            (entry.date, entry.net_worth)
            for entry in sorted(self.entries, key=lambda e: e.date)
            if entry.net_worth is not None
        ]
    
    def to_dict(self) -> dict:
        """Convert dataset to dictionary for JSON serialization."""
        return {
            "entries": [entry.to_dict() for entry in self.entries],
            "source_sheet_id": self.source_sheet_id,
            "source_sheet_name": self.source_sheet_name,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "entry_count": len(self.entries),
        }
