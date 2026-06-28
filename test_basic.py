#!/usr/bin/env python3
"""
Basic test to verify the project structure, imports, and URL generation
work correctly against the current Kleinanzeigen URL scheme.

If any check fails, the script exits with a non-zero status and a
clear summary of which checks failed.
"""

import sys
import os
import traceback

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


_failures = []


def _record(name: str, ok: bool, detail: str = ""):
    status = "✅" if ok else "❌"
    print(f"  {status} {name}" + (f"  ({detail})" if detail else ""))
    if not ok:
        _failures.append(name)


def test_imports():
    """Test that all imports work"""
    print("\n[1] Imports")
    try:
        from config.settings import Settings, settings
        _record("config.settings", True)
    except Exception as e:
        _record("config.settings", False, str(e))
        return

    try:
        from scraper.models import Listing, ScrapeResult
        _record("scraper.models", True)
    except Exception as e:
        _record("scraper.models", False, str(e))

    try:
        from scraper.utils import (
            parse_kleinanzeigen_date,
            calculate_age_days,
            generate_search_url,
            generate_all_category_urls,
            get_random_user_agent,
            build_page_url,
        )
        _record("scraper.utils", True)
    except Exception as e:
        _record("scraper.utils", False, str(e))

    try:
        from scraper.kleinanzeigen import KleinanzeigenScraper, scrape_kleinanzeigen
        _record("scraper.kleinanzeigen", True)
    except Exception as e:
        _record("scraper.kleinanzeigen", False, str(e))

    try:
        from scraper.exporter import ExcelExporter, export_to_excel
        _record("scraper.exporter", True)
    except Exception as e:
        _record("scraper.exporter", False, str(e))


def test_date_parsing():
    """Test date parsing for every format used by Kleinanzeigen."""
    print("\n[2] Date parsing")
    from scraper.utils import parse_kleinanzeigen_date
    from datetime import datetime, timedelta

    cases = [
        # (input, expected_offset_days, description)
        ("Heute",          0,   "today"),
        ("Gestern",        1,   "yesterday"),
        ("vor 2 Tagen",    2,   "N days ago"),
        ("vor 3 Wochen",   21,  "N weeks ago"),
        ("vor 2 Monaten",  None, "N months ago (varies)"),
        ("vor 1 Jahren",   None, "N years ago (varies)"),
        ("01.01.2024",     None, "DD.MM.YYYY"),
        ("Januar 2024",    None, "Month YYYY"),
    ]
    for raw, expected_days, desc in cases:
        parsed = parse_kleinanzeigen_date(raw)
        if expected_days is None:
            # Just check it's parseable
            _record(desc, parsed is not None, f"got {parsed!r}")
        else:
            if parsed is None:
                _record(desc, False, "returned None")
            else:
                delta = (datetime.now() - parsed).days
                _record(desc, delta == expected_days, f"got {delta} days")


def test_settings():
    """Test settings configuration."""
    print("\n[3] Settings")
    from config.settings import Settings
    _record("BASE_URL set", Settings.BASE_URL.startswith("https://"), Settings.BASE_URL)
    _record("REQUEST_DELAY is (min, max) tuple", isinstance(Settings.REQUEST_DELAY, tuple)
            and len(Settings.REQUEST_DELAY) == 2)
    _record("MAX_PAGES > 0", Settings.MAX_PAGES > 0, str(Settings.MAX_PAGES))
    _record("MIN_AGE_DAYS == 90", Settings.MIN_AGE_DAYS == 90, str(Settings.MIN_AGE_DAYS))
    _record("IMMOBILIEN_CATEGORY == c195", Settings.IMMOBILIEN_CATEGORY == "c195",
            Settings.IMMOBILIEN_CATEGORY)
    _record("Output dir exists or can be created", Settings.OUTPUT_DIR.exists())


def test_bundesland_mapping():
    """Test Bundesland mapping has locationIds."""
    print("\n[4] Bundesland mapping")
    import json
    from config.settings import Settings
    try:
        with open(Settings.BUNDESLAND_MAPPING_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        _record("load mapping file", False, str(e))
        return

    _record("loaded 16 Bundesländer", len(data) == 16, f"{len(data)} entries")

    missing_loc_id = [name for name, info in data.items() if not info.get("location_id")]
    _record("every entry has a location_id", len(missing_loc_id) == 0,
            "missing: " + ", ".join(missing_loc_id) if missing_loc_id else "")

    # Check that the well-known mapping for NRW, Bayern, Berlin works
    expected = {
        "Bayern": "5510",
        "Berlin": "3331",
        "Nordrhein-Westfalen": "928",
        "Bremen": "1",
    }
    for name, loc_id in expected.items():
        actual = data.get(name, {}).get("location_id")
        _record(f"{name} -> locationId={loc_id}", actual == loc_id, f"got {actual}")


def test_url_generation():
    """Test that URLs use the modern locationId + category-code format."""
    print("\n[5] URL generation")
    from scraper.utils import generate_search_url, generate_all_category_urls, build_page_url

    # Page 1 with locationId
    url = generate_search_url("bayern", 1, "5510")
    expected = ("https://www.kleinanzeigen.de/s-immobilien/bayern/c195l5510"
                "?posterType=PRIVATE&sortingField=SORTING_DATE")
    _record(f"page 1 with locationId", url == expected, f"got {url}")

    # Page 2 should use ?o=2 appended to the default query
    url = generate_search_url("bayern", 2, "5510")
    expected = ("https://www.kleinanzeigen.de/s-immobilien/bayern/c195l5510"
                "?posterType=PRIVATE&sortingField=SORTING_DATE&o=2")
    _record(f"page 2 uses ?o=", url == expected, f"got {url}")

    # The default query params must always be present (so private-only + sort-by-date)
    _record("default query contains posterType=PRIVATE",
            "posterType=PRIVATE" in url)
    _record("default query contains sortingField=SORTING_DATE",
            "sortingField=SORTING_DATE" in url)

    # Sub-category URLs should use the modern category-code scheme
    urls = generate_all_category_urls("bremen", "1")
    _record("generate_all_category_urls returns URLs",
            len(urls) > 0, f"{len(urls)} URLs")
    # Each URL should have the region slug, a category code, locationId, and the default params
    sample = urls[0] if urls else ""
    _record("URL uses /bremen/c<code>l<locationId> format",
            "/bremen/c" in sample and "l1" in sample,
            f"sample: {sample}")
    _record("URL has posterType=PRIVATE filter",
            all("posterType=PRIVATE" in u for u in urls))
    _record("URL has sortingField=SORTING_DATE",
            all("sortingField=SORTING_DATE" in u for u in urls))

    # Sub-categories should include c208 (Häuser zum Kauf), where the user's
    # example listing lives.
    cat_codes = [u.split("/")[-1].split("l")[0].split("?")[0] for u in urls]
    _record("subcategory list contains c208 (Häuser zum Kauf)",
            "c208" in cat_codes, f"codes: {cat_codes}")

    # build_page_url should produce paginated URL
    base = ("https://www.kleinanzeigen.de/s-immobilien/bremen/c195l1"
            "?posterType=PRIVATE&sortingField=SORTING_DATE")
    p2 = build_page_url(base, 2)
    _record("build_page_url page 2", p2 == base + "&o=2", f"got {p2}")
    _record("build_page_url page 1 == base", build_page_url(base, 1) == base)


def test_min_age_filter():
    """Test that Listing.is_older_than_3_months works."""
    print("\n[6] Age filter")
    from scraper.models import Listing
    from datetime import datetime, timedelta

    fresh = Listing(title="t", url="u", date_parsed=datetime.now() - timedelta(days=10))
    old = Listing(title="t", url="u", date_parsed=datetime.now() - timedelta(days=120))
    boundary = Listing(title="t", url="u", date_parsed=datetime.now() - timedelta(days=91))
    nodate = Listing(title="t", url="u")

    _record("10-day-old listing is not old", not fresh.is_older_than_3_months)
    _record("120-day-old listing IS old", old.is_older_than_3_months)
    _record("91-day-old listing IS old", boundary.is_older_than_3_months)
    _record("listing with no date is not old", not nodate.is_older_than_3_months)


def main():
    print("=" * 60)
    print("Kleinanzeigen Scraper - Tests")
    print("=" * 60)

    tests = [
        test_imports,
        test_date_parsing,
        test_settings,
        test_bundesland_mapping,
        test_url_generation,
        test_min_age_filter,
    ]
    for t in tests:
        try:
            t()
        except Exception as e:
            _record(t.__name__, False, str(e))
            traceback.print_exc()

    print("\n" + "=" * 60)
    if _failures:
        print(f"❌ {len(_failures)} check(s) FAILED:")
        for name in _failures:
            print(f"   - {name}")
        print("=" * 60)
        return 1
    else:
        print("✅ All checks passed")
        print("=" * 60)
        return 0


if __name__ == "__main__":
    sys.exit(main())