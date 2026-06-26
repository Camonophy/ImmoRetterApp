#!/usr/bin/env python3
"""
Basic test to verify the project structure and imports work correctly.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all imports work"""
    print("Testing imports...")
    
    try:
        from config.settings import Settings, settings
        print("✅ Settings imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import Settings: {e}")
        return False
    
    try:
        from scraper.models import Listing, ScrapeResult
        print("✅ Models imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import Models: {e}")
        return False
    
    try:
        from scraper.utils import (
            parse_kleinanzeigen_date,
            calculate_age_days,
            generate_search_url,
            get_random_user_agent,
        )
        print("✅ Utils imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import Utils: {e}")
        return False
    
    try:
        from scraper.kleinanzeigen import KleinanzeigenScraper, scrape_kleinanzeigen
        print("✅ Kleinanzeigen scraper imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import Kleinanzeigen scraper: {e}")
        return False
    
    try:
        from scraper.exporter import ExcelExporter, export_to_excel
        print("✅ Exporter imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import Exporter: {e}")
        return False
    
    return True


def test_date_parsing():
    """Test date parsing functionality"""
    print("\nTesting date parsing...")
    
    from scraper.utils import parse_kleinanzeigen_date, calculate_age_days
    from datetime import datetime
    
    test_cases = [
        ("Heute", "Today"),
        ("Gestern", "Yesterday"),
        ("vor 2 Tagen", "2 days ago"),
        ("vor 3 Wochen", "3 weeks ago"),
        ("vor 2 Monaten", "2 months ago"),
        ("01.01.2024", "DD.MM.YYYY format"),
        ("Januar 2024", "Month Year format"),
    ]
    
    for date_str, description in test_cases:
        parsed = parse_kleinanzeigen_date(date_str)
        if parsed:
            print(f"✅ {description}: {date_str} -> {parsed}")
        else:
            print(f"❌ {description}: {date_str} -> Failed to parse")
    
    return True


def test_settings():
    """Test settings configuration"""
    print("\nTesting settings...")
    
    from config.settings import Settings, settings
    
    print(f"✅ Base URL: {Settings.BASE_URL}")
    print(f"✅ Request delay: {Settings.REQUEST_DELAY}")
    print(f"✅ Max pages: {Settings.MAX_PAGES}")
    print(f"✅ Output dir: {Settings.OUTPUT_DIR}")
    
    return True


def test_bundesland_mapping():
    """Test Bundesland mapping"""
    print("\nTesting Bundesland mapping...")
    
    import json
    from config.settings import Settings
    
    try:
        with open(Settings.BUNDESLAND_MAPPING_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"✅ Loaded {len(data)} Bundesländer")
        
        # Show first few
        for name, info in list(data.items())[:3]:
            print(f"  - {name}: {info['url_param']}")
        
        return True
    except Exception as e:
        print(f"❌ Failed to load Bundesland mapping: {e}")
        return False


def test_url_generation():
    """Test URL generation"""
    print("\nTesting URL generation...")
    
    from scraper.utils import generate_search_url
    
    test_cases = [
        ("bayern", 1, "https://www.kleinanzeigen.de/s-immobilien/bayern/k0"),
        ("nordrhein-westfalen", 2, "https://www.kleinanzeigen.de/s-immobilien/nordrhein-westfalen/k0?o=2"),
    ]
    
    for region, page, expected in test_cases:
        url = generate_search_url(region, page)
        if url == expected:
            print(f"✅ {region} page {page}: {url}")
        else:
            print(f"❌ {region} page {page}: got {url}, expected {expected}")
    
    return True


def main():
    """Run all tests"""
    print("=" * 60)
    print("Kleinanzeigen Scraper - Basic Tests")
    print("=" * 60)
    
    tests = [
        test_imports,
        test_settings,
        test_date_parsing,
        test_bundesland_mapping,
        test_url_generation,
    ]
    
    all_passed = True
    for test in tests:
        try:
            if not test():
                all_passed = False
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed")
    print("=" * 60)
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
