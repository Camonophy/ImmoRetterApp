"""
Settings and configuration for Kleinanzeigen.de Real Estate Scraper
"""

import os
from pathlib import Path
from typing import Tuple


class Settings:
    """Application settings"""
    
    # Base URLs
    BASE_URL = "https://www.kleinanzeigen.de"
    SEARCH_PATH = "/s-immobilien/{region}/k0"
    
    # Request configuration
    REQUEST_DELAY: Tuple[int, int] = (2, 5)  # Random delay between requests in seconds
    MAX_PAGES = 100  # Maximum pages to scrape (safety limit)
    REQUEST_TIMEOUT = 30  # Request timeout in seconds
    MAX_RETRIES = 3  # Maximum retries for failed requests
    
    # User agents for rotation
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/91.0.864.59 Safari/537.36",
    ]
    
    # File paths
    PROJECT_ROOT = Path(__file__).parent.parent
    DATA_DIR = PROJECT_ROOT / "data"
    OUTPUT_DIR = DATA_DIR / "output"
    BUNDESLAND_MAPPING_FILE = DATA_DIR / "bundesland_mapping.json"
    
    # Logging
    LOG_LEVEL = "INFO"
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE = PROJECT_ROOT / "scraper.log"
    
    # Date filtering
    MIN_AGE_DAYS = 90  # Listings older than this will be included
    
    # Excel output
    EXCEL_FILENAME_TEMPLATE = "{bundesland}_real_estate_old_listings_{timestamp}.xlsx"
    EXCEL_DATE_FORMAT = "%Y-%m-%d_%H-%M-%S"
    
    # Headers for HTTP requests
    DEFAULT_HEADERS = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "de-DE,de;q=0.8,en-US;q=0.5,en;q=0.3",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "DNT": "1",
    }
    
    # Kleinanzeigen specific
    REAL_ESTATE_CATEGORY = "k0"  # All real estate categories
    
    # Validate and create directories
    @classmethod
    def validate_directories(cls):
        """Ensure required directories exist"""
        cls.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)


# Initialize settings
Settings.validate_directories()

# Create a settings instance for easy access
settings = Settings()
