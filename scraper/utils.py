"""
Utility functions for Kleinanzeigen Scraper
"""

import random
import re
from datetime import datetime, timedelta
from typing import Optional
from dateutil.parser import parse as parse_date
from dateutil.relativedelta import relativedelta

from .models import Listing
from config.settings import Settings


def get_random_user_agent() -> str:
    """Get a random user agent from settings"""
    return random.choice(Settings.USER_AGENTS)


def generate_search_url(bundesland_url_param: str, page: int = 1) -> str:
    """
    Generate Kleinanzeigen search URL for a Bundesland
    
    Args:
        bundesland_url_param: URL parameter for the Bundesland
        page: Page number (1-based)
    
    Returns:
        Complete search URL
    """
    base_url = Settings.BASE_URL.rstrip("/")
    search_path = Settings.SEARCH_PATH.format(region=bundesland_url_param)
    
    # Kleinanzeigen uses ?o=1 for page 1, ?o=2 for page 2, etc.
    if page == 1:
        return f"{base_url}{search_path}"
    else:
        return f"{base_url}{search_path}?o={page}"


def parse_kleinanzeigen_date(date_str: str) -> Optional[datetime]:
    """
    Parse Kleinanzeigen date string into datetime object
    
    Handles various date formats:
    - "Heute" (Today)
    - "Gestern" (Yesterday)
    - "vor 2 Tagen" (2 days ago)
    - "vor 3 Wochen" (3 weeks ago)
    - "vor 2 Monaten" (2 months ago)
    - "01.01.2024" (DD.MM.YYYY)
    - "Jan 2024" (Month Year)
    
    Args:
        date_str: Date string from Kleinanzeigen
    
    Returns:
        datetime object or None if parsing fails
    """
    if not date_str:
        return None
    
    date_str = date_str.strip().lower()
    
    # Handle "Heute" (Today)
    if date_str == "heute":
        return datetime.now()
    
    # Handle "Gestern" (Yesterday)
    if date_str == "gestern":
        return datetime.now() - timedelta(days=1)
    
    # Handle "vor X Tagen" (X days ago)
    match = re.match(r"vor (\d+) tagen?", date_str)
    if match:
        days = int(match.group(1))
        return datetime.now() - timedelta(days=days)
    
    # Handle "vor X Wochen" (X weeks ago)
    match = re.match(r"vor (\d+) wochen?", date_str)
    if match:
        weeks = int(match.group(1))
        return datetime.now() - timedelta(weeks=weeks)
    
    # Handle "vor X Monaten" (X months ago)
    match = re.match(r"vor (\d+) monaten?", date_str)
    if match:
        months = int(match.group(1))
        return datetime.now() - relativedelta(months=months)
    
    # Handle "vor X Jahren" (X years ago)
    match = re.match(r"vor (\d+) jahren?", date_str)
    if match:
        years = int(match.group(1))
        return datetime.now() - relativedelta(years=years)
    
    # Handle DD.MM.YYYY format
    match = re.match(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", date_str)
    if match:
        day, month, year = match.groups()
        try:
            return datetime(int(year), int(month), int(day))
        except ValueError:
            pass
    
    # Handle MM.YYYY or Month YYYY format
    match = re.match(r"(\d{1,2})\.(\d{4})", date_str)
    if match:
        month, year = match.groups()
        try:
            return datetime(int(year), int(month), 1)
        except ValueError:
            pass
    
    # Handle month names (German)
    month_names = {
        "januar": 1, "jan": 1,
        "februar": 2, "feb": 2,
        "märz": 3, "maerz": 3, "mar": 3,
        "april": 4, "apr": 4,
        "mai": 5, "may": 5,
        "juni": 6, "jun": 6,
        "juli": 7, "jul": 7,
        "august": 8, "aug": 8,
        "september": 9, "sep": 9, "sept": 9,
        "oktober": 10, "okt": 10, "oct": 10,
        "november": 11, "nov": 11,
        "dezember": 12, "dez": 12, "dec": 12,
    }
    
    # Handle "Monat YYYY" format (e.g., "Januar 2024")
    match = re.match(r"([a-zäöü]+) (\d{4})", date_str)
    if match:
        month_name, year = match.groups()
        month_name = month_name.lower()
        if month_name in month_names:
            try:
                return datetime(int(year), month_names[month_name], 1)
            except ValueError:
                pass
    
    # Try generic date parsing as fallback
    try:
        return parse_date(date_str, dayfirst=True, yearfirst=False)
    except (ValueError, TypeError):
        pass
    
    # If all else fails, return None
    return None


def calculate_age_days(date_str: str) -> Optional[int]:
    """
    Calculate age in days from a Kleinanzeigen date string
    
    Args:
        date_str: Date string from Kleinanzeigen
    
    Returns:
        Age in days or None if parsing fails
    """
    parsed_date = parse_kleinanzeigen_date(date_str)
    if parsed_date:
        delta = datetime.now() - parsed_date
        return delta.days
    return None


def is_older_than_3_months(date_str: str) -> bool:
    """
    Check if a listing is older than 3 months
    
    Args:
        date_str: Date string from Kleinanzeigen
    
    Returns:
        True if older than 3 months, False otherwise
    """
    age_days = calculate_age_days(date_str)
    if age_days is not None:
        return age_days > 90
    return False


def extract_listing_id(url: str) -> Optional[str]:
    """
    Extract listing ID from Kleinanzeigen URL
    
    Args:
        url: Kleinanzeigen listing URL
    
    Returns:
        Listing ID or None
    """
    if not url:
        return None
    
    # URL format: https://www.kleinanzeigen.de/s-anzeige/123456789-abc-def/...
    match = re.search(r"/s-anzeige/(\d+)-[^/]+", url)
    if match:
        return match.group(1)
    
    return None


def normalize_price(price_str: str) -> Optional[str]:
    """
    Normalize price string (remove currency symbols, commas, etc.)
    
    Args:
        price_str: Price string from Kleinanzeigen
    
    Returns:
        Normalized price string or None
    """
    if not price_str:
        return None
    
    # Remove currency symbols and whitespace
    price_str = price_str.strip()
    price_str = re.sub(r"[€$\s]", "", price_str)
    
    # Replace comma with dot for decimal
    price_str = price_str.replace(",", ".")
    
    return price_str if price_str else None


def normalize_location(location_str: str) -> Optional[str]:
    """
    Normalize location string
    
    Args:
        location_str: Location string from Kleinanzeigen
    
    Returns:
        Normalized location string or None
    """
    if not location_str:
        return None
    
    return location_str.strip()
