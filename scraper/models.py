"""
Data models for Kleinanzeigen Scraper
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List


@dataclass
class Listing:
    """Represents a single Kleinanzeigen listing"""
    
    title: str
    url: str
    price: Optional[str] = None
    location: Optional[str] = None
    date_posted: Optional[str] = None
    date_parsed: Optional[datetime] = None
    age_days: Optional[int] = None
    is_older_than_3_months: bool = False
    
    def __post_init__(self):
        """Calculate derived fields after initialization"""
        if self.date_parsed:
            self.age_days = self.calculate_age()
            self.is_older_than_3_months = self.age_days > 90 if self.age_days else False
    
    def calculate_age(self) -> Optional[int]:
        """Calculate age in days from parsed date"""
        if self.date_parsed:
            delta = datetime.now() - self.date_parsed
            return delta.days
        return None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for Excel export"""
        return {
            "Title": self.title,
            "URL": self.url,
            "Price": self.price or "",
            "Location": self.location or "",
            "Date Posted": self.date_posted or "",
            "Age (Days)": self.age_days or "",
            "Older than 3 months": "Yes" if self.is_older_than_3_months else "No",
        }


@dataclass
class ScrapeResult:
    """Represents the result of a scraping operation"""
    
    bundesland: str
    total_listings_found: int = 0
    old_listings_found: int = 0
    listings: List[Listing] = field(default_factory=list)
    pages_scraped: int = 0
    errors: List[str] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate duration in seconds"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    def get_old_listings(self) -> List[Listing]:
        """Get only listings older than 3 months"""
        return [listing for listing in self.listings if listing.is_older_than_3_months]
    
    def to_summary_dict(self) -> dict:
        """Convert to summary dictionary"""
        return {
            "Bundesland": self.bundesland,
            "Total Listings Found": self.total_listings_found,
            "Old Listings (>3 months)": self.old_listings_found,
            "Pages Scraped": self.pages_scraped,
            "Duration (seconds)": self.duration_seconds,
            "Errors": len(self.errors),
        }
