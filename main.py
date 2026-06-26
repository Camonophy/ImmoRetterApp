#!/usr/bin/env python3
"""
Kleinanzeigen.de Real Estate Scraper

Main entry point for the application.
Scrapes Kleinanzeigen.de for real estate listings in a specified Bundesland,
filters for listings older than 3 months, and exports to Excel.
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Optional

from scraper.kleinanzeigen import scrape_kleinanzeigen
from scraper.exporter import export_to_excel
from scraper.models import ScrapeResult
from config.settings import Settings

# Set up logging
logging.basicConfig(
    level=Settings.LOG_LEVEL,
    format=Settings.LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(Settings.LOG_FILE),
    ]
)
logger = logging.getLogger(__name__)


def load_bundesland_mapping() -> dict:
    """Load Bundesland to URL parameter mapping"""
    try:
        with open(Settings.BUNDESLAND_MAPPING_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Create a simple mapping of name to url_param
        mapping = {}
        for name, info in data.items():
            mapping[name] = info["url_param"]
        
        return mapping
    except FileNotFoundError:
        logger.error(f"Bundesland mapping file not found: {Settings.BUNDESLAND_MAPPING_FILE}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing Bundesland mapping file: {e}")
        return {}


def get_available_bundeslaender() -> list:
    """Get list of available Bundesländer"""
    mapping = load_bundesland_mapping()
    return sorted(mapping.keys())


def validate_bundesland(bundesland: str) -> tuple:
    """
    Validate Bundesland input
    
    Args:
        bundesland: Bundesland name to validate
    
    Returns:
        Tuple of (is_valid, bundesland_name, url_param)
    """
    mapping = load_bundesland_mapping()
    
    # Check exact match
    if bundesland in mapping:
        return True, bundesland, mapping[bundesland]
    
    # Check case-insensitive match
    bundesland_lower = bundesland.lower()
    for name, url_param in mapping.items():
        if name.lower() == bundesland_lower:
            return True, name, url_param
    
    # Check partial match
    matches = [name for name in mapping.keys() if bundesland_lower in name.lower()]
    if len(matches) == 1:
        return True, matches[0], mapping[matches[0]]
    elif len(matches) > 1:
        return False, None, None  # Multiple matches - ambiguous
    
    return False, None, None


def print_available_bundeslaender():
    """Print list of available Bundesländer"""
    bundeslaender = get_available_bundeslaender()
    
    print("\nAvailable Bundesländer:")
    print("-" * 40)
    for i, bundesland in enumerate(bundeslaender, 1):
        print(f"{i:2d}. {bundesland}")
    print()


def run_scrape(bundesland: str, export_all: bool = False) -> Optional[str]:
    """
    Run the scraping process for a Bundesland
    
    Args:
        bundesland: Name of the Bundesland to scrape
        export_all: If True, export all listings (not just old ones)
    
    Returns:
        Path to exported Excel file or None if failed
    """
    # Validate Bundesland
    is_valid, bundesland_name, url_param = validate_bundesland(bundesland)
    
    if not is_valid:
        logger.error(f"Unknown Bundesland: {bundesland}")
        print(f"Error: Unknown Bundesland '{bundesland}'")
        print_available_bundeslaender()
        return None
    
    logger.info(f"Starting scrape for: {bundesland_name}")
    print(f"Scraping real estate listings for: {bundesland_name}")
    print("This may take a few minutes...")
    
    # Perform scraping
    try:
        result = scrape_kleinanzeigen(bundesland_name, url_param)
    except Exception as e:
        logger.error(f"Error during scraping: {e}")
        print(f"Error: {e}")
        return None
    
    # Export results
    if export_all:
        from scraper.exporter import ExcelExporter
        exporter = ExcelExporter()
        filepath = exporter.export_all_listings(result)
    else:
        filepath = export_to_excel(result)
    
    if filepath:
        print(f"\n✅ Success!")
        print(f"Found {result.total_listings_found} total listings")
        print(f"Found {result.old_listings_found} listings older than 3 months")
        print(f"Scraped {result.pages_scraped} pages in {result.duration_seconds:.1f} seconds")
        print(f"\nExported to: {filepath}")
        
        if result.errors:
            print(f"\n⚠️  {len(result.errors)} errors occurred during scraping")
            for error in result.errors[:5]:  # Show first 5 errors
                print(f"  - {error}")
    else:
        print("No old listings found or error during export")
    
    return filepath


def interactive_mode():
    """Run in interactive mode"""
    print("=" * 60)
    print("Kleinanzeigen.de Real Estate Scraper")
    print("=" * 60)
    print()
    
    # Show available Bundesländer
    print_available_bundeslaender()
    
    # Get user input
    while True:
        bundesland = input("Enter Bundesland name (or 'list' to show options, 'quit' to exit): ").strip()
        
        if bundesland.lower() == 'quit':
            print("Goodbye!")
            break
        elif bundesland.lower() == 'list':
            print_available_bundeslaender()
            continue
        elif not bundesland:
            continue
        
        # Ask about export option
        export_all = input("Export ALL listings or only old ones? (all/old, default: old): ").strip().lower()
        export_all_flag = export_all == 'all'
        
        # Run scrape
        run_scrape(bundesland, export_all_flag)
        print()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Kleinanzeigen.de Real Estate Scraper - Scrape real estate listings older than 3 months",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --bundesland "Bayern"
  python main.py -b "Nordrhein-Westfalen" --all
  python main.py --list
  python main.py -i  # Interactive mode
        """
    )
    
    parser.add_argument(
        "-b", "--bundesland",
        type=str,
        help="Bundesland to scrape (e.g., 'Bayern', 'Nordrhein-Westfalen')"
    )
    
    parser.add_argument(
        "--all",
        action="store_true",
        help="Export ALL listings (not just those older than 3 months)"
    )
    
    parser.add_argument(
        "-l", "--list",
        action="store_true",
        help="List available Bundesländer and exit"
    )
    
    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="Run in interactive mode"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Handle verbose logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # List Bundesländer and exit
    if args.list:
        print_available_bundeslaender()
        return
    
    # Interactive mode
    if args.interactive:
        interactive_mode()
        return
    
    # Check if Bundesland is provided
    if not args.bundesland:
        parser.print_help()
        print("\nPlease specify a Bundesland with --bundesland or -b")
        print("Use --list to see available options")
        return
    
    # Run scrape with provided Bundesland
    run_scrape(args.bundesland, args.all)


if __name__ == "__main__":
    main()
