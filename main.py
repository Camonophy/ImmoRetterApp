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
    """Load the full Bundesland mapping (name -> info dict)."""
    try:
        with open(Settings.BUNDESLAND_MAPPING_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Bundesland mapping file not found: {Settings.BUNDESLAND_MAPPING_FILE}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing Bundesland mapping file: {e}")
        return {}


def get_available_bundeslaender() -> list:
    """Return a sorted list of all configured Bundesländer."""
    return sorted(load_bundesland_mapping().keys())


def validate_bundesland(bundesland: str) -> tuple:
    """
    Validate a Bundesland name.

    Returns (is_valid, display_name, url_param, location_id).
    """
    mapping = load_bundesland_mapping()

    # Exact match
    if bundesland in mapping:
        info = mapping[bundesland]
        return True, bundesland, info["url_param"], info.get("location_id")

    # Case-insensitive match
    bl_lower = bundesland.lower()
    for name, info in mapping.items():
        if name.lower() == bl_lower:
            return True, name, info["url_param"], info.get("location_id")

    # Partial match — only if unambiguous
    matches = [name for name in mapping.keys() if bl_lower in name.lower()]
    if len(matches) == 1:
        info = mapping[matches[0]]
        return True, matches[0], info["url_param"], info.get("location_id")

    return False, None, None, None


def print_available_bundeslaender():
    """Print the list of available Bundesländer."""
    bundeslaender = get_available_bundeslaender()
    print("\nAvailable Bundesländer:")
    print("-" * 40)
    for i, bl in enumerate(bundeslaender, 1):
        print(f"{i:2d}. {bl}")
    print()


def run_scrape(bundesland: str, export_all: bool = False) -> Optional[str]:
    """
    Run the scraping process for a Bundesland.

    Args:
        bundesland: Display name of the Bundesland.
        export_all: If True, export every listing (not just old ones).

    Returns:
        Path to the exported Excel file, or None if nothing was exported.
    """
    is_valid, bl_name, url_param, location_id = validate_bundesland(bundesland)
    if not is_valid:
        logger.error(f"Unknown Bundesland: {bundesland}")
        print(f"Error: Unknown Bundesland '{bundesland}'")
        print_available_bundeslaender()
        return None

    logger.info(f"Starting scrape for: {bl_name} (locationId={location_id})")
    print(f"Scraping real estate listings for: {bl_name}")
    print("This may take a few minutes...")

    try:
        result = scrape_kleinanzeigen(bl_name, url_param, location_id)
    except Exception as e:
        logger.error(f"Error during scraping: {e}")
        print(f"Error: {e}")
        return None

    # Decide what to export
    filepath = export_to_excel(result, allow_all_fallback=export_all)
    if export_all:
        # --all: write everything we found
        filepath = filepath or export_to_excel(result, allow_all_fallback=True)

    print(f"\nSummary for {bl_name}:")
    print(f"  Total listings found : {result.total_listings_found}")
    print(f"  Older than 3 months  : {result.old_listings_found}")
    print(f"  Pages scraped        : {result.pages_scraped}")
    print(f"  Duration             : {result.duration_seconds:.1f} seconds")

    if filepath:
        kind = "all listings" if export_all else "old listings only"
        print(f"\nExported ({kind}) to: {filepath}")
    else:
        if export_all:
            print("\nNo listings to export.")
        else:
            print("\nNo listings older than 3 months found.")
            print("(Re-run with --all to export every listing regardless of age.)")

    if result.errors:
        print(f"\n{len(result.errors)} error(s) during scraping:")
        for err in result.errors[:5]:
            print(f"  - {err}")

    return filepath


def interactive_mode():
    """Run in interactive mode."""
    print("=" * 60)
    print("Kleinanzeigen.de Real Estate Scraper")
    print("=" * 60)
    print()

    print_available_bundeslaender()

    while True:
        bundesland = input("Enter Bundesland name (or 'list' to show options, 'quit' to exit): ").strip()

        if bundesland.lower() == 'quit':
            print("Goodbye!")
            break
        if bundesland.lower() == 'list':
            print_available_bundeslaender()
            continue
        if not bundesland:
            continue

        export_all = input("Export ALL listings or only old ones? (all/old, default: old): ").strip().lower()
        export_all_flag = export_all == 'all'

        run_scrape(bundesland, export_all_flag)
        print()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Kleinanzeigen.de Real Estate Scraper — scrape listings older than 3 months in a given Bundesland.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --bundesland "Bayern"
  python main.py -b "Nordrhein-Westfalen" --all
  python main.py --list
  python main.py -i
        """
    )

    parser.add_argument("-b", "--bundesland", type=str,
                        help="Bundesland to scrape (e.g. 'Bayern', 'Nordrhein-Westfalen')")
    parser.add_argument("--all", action="store_true",
                        help="Export ALL listings (not just those older than 3 months)")
    parser.add_argument("-l", "--list", action="store_true",
                        help="List available Bundesländer and exit")
    parser.add_argument("-i", "--interactive", action="store_true",
                        help="Run in interactive mode")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Enable verbose (DEBUG) logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.list:
        print_available_bundeslaender()
        return

    if args.interactive:
        interactive_mode()
        return

    if not args.bundesland:
        parser.print_help()
        print("\nPlease specify a Bundesland with --bundesland or -b")
        print("Use --list to see available options")
        return

    run_scrape(args.bundesland, args.all)


if __name__ == "__main__":
    main()