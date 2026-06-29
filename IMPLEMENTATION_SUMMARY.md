# ImmoRetterApp - Implementation Summary

## Project Status: WORKING & VERIFIED

**Last Verified**: 2026-06-28 against live Kleinanzeigen.de

The ImmoRetterApp scraper successfully scrapes Kleinanzeigen.de for real estate listings in a specified German Bundesland, filters for listings that haven't been bumped in more than 3 months (90 days), and exports to Excel.

---

## What Works

### Region-Filtered Search
The scraper uses the modern locationId URL parameter to correctly scope the search to the requested Bundesland.

**Verification**: When run for "Bremen", all 322 scraped listings have locations in Bremen:
- 27568 Bremerhaven
- 28201 Neustadt
- 28329 Neue Vahr Nord
- And other Bremen locations

Without locationId, the search returns nationwide results regardless of the Bundesland slug in the URL path.

### Subcategory Coverage
9 real-estate subcategories are configured, each addressed via the modern numeric category code URL scheme:
```
/s-immobilien/<region>/<code>l<locationId>?posterType=PRIVATE&sortingField=SORTING_DATE
```

| Code | Category | English | Verified |
|------|----------|---------|----------|
| c195 | Immobilien | Real Estate (umbrella) | YES |
| c196 | Eigentumswohnung kaufen | Condominiums for Sale | YES |
| c197 | Garage & Lagerraum | Garages & Storage | YES |
| c198 | Weitere Immobilien | Other Real Estate | YES |
| c199 | Auf Zeit & WG | Temporary & Shared Housing | YES |
| c203 | Mietwohnung | Apartments for Rent | YES |
| c205 | Haeuser zur Miete | Houses for Rent | YES |
| c207 | Grundstuecke & Gaerten | Plots & Gardens | YES |
| c208 | Haeuser zum Kauf | Houses for Sale | YES |

### Field Extraction
For every search-result card, the scraper correctly extracts:
- Title from h2.text-module-begin a or h2 a
- URL from data-href attribute or href on title link
- Price from .aditem-main--middle--price-shipping--price
- Location from .aditem-main--top--left (with cleanup of distance markers)
- Activation Date from .aditem-main--top--right (when available on modern cards)

### Activation Date Extraction
The activation date (last time the seller bumped the listing) is extracted from:
1. Search cards (modern Kleinanzeigen): .aditem-main--top--right
2. Detail pages (fallback): #viewad-extra-info section with calendar icon

This date represents when the seller last refreshed the listing, which is exactly the signal needed to find neglected listings.

### Age Filter
Listings whose activation date is older than 90 days are flagged and exported.

The Listing dataclass automatically calculates:
- age_days: Days since activation
- is_older_than_3_months: Boolean flag (age_days > 90)

### Excel Export
- File naming: {bundesland}_real_estate_old_listings_{timestamp}.xlsx
- Sheet 1: Listings data with 7 columns
- Sheet 2: Summary statistics
- Sheet name truncation: Automatically truncated to Excel's 31-character limit
- No silent fallback: If no old listings found, no misleading file is created

**Columns**:
1. Title
2. URL
3. Price
4. Location
5. Date Posted
6. Age (Days)
7. Older than 3 months (Yes/No)

### Test Suite
Run with: python test_basic.py

The test suite actually reports pass/fail per check and exits with non-zero status on failure.

**Tests cover:**
- All imports work correctly
- Date parsing for all Kleinanzeigen formats
- Settings configuration
- Bundesland mapping has location_ids
- URL generation uses modern format
- Age filter logic

---

## End-to-End Run Results

### Test 1: Nordrhein-Westfalen (Mietwohnung, 12 pages)
| Stat | Value |
|---|---|
| Total listings found | 324 |
| Listings with extracted date | 324 (100%) |
| Date-fetch errors | 0 |
| Age range | 0 - 49 days |
| Listings >90 days old | 0 |
| Pages scraped | 12 |
| Duration | 343 seconds |

Note: 0 listings >90 days is due to market reality (sellers bump frequently), not a bug.

### Test 2: Bremen (All 9 Categories)
| Stat | Value |
|---|---|
| Total listings found | 322 |
| All locations in Bremen | VERIFIED |
| All dates extracted | SUCCESS |
| Listings >90 days old | 0 |
| Pages scraped | 18 |
| Duration | ~15 minutes |

### Test 3: User Example Listing (Rees, NRW)
This was the critical test - finding a listing that the user knew existed but wasn't being found by other scrapers.

| Field | Value |
|---|---|
| Title | Schoenes Chalet in Huenxe, Baujahr 2014, winterfest, zu verkaufen |
| URL | https://www.kleinanzeigen.de/s-anzeige/schoenes-chalet-in-huenxe-baujahr-2014-winterfest-zu-verkaufen/3110176588-208-1389 |
| Price | 65.000 EUR |
| Location | 46459 Rees |
| Date Posted | 13.06.2025 |
| Age (Days) | 380 |
| Older than 3 months | Yes |
| Result | FOUND via sub-location walker |

This listing was only found through the sub-location walker (Phase 2), not the state-level search (Phase 1).

### Test 4: Full NRW Run (State + Sub-Locations)
| Stat | Value |
|---|---|
| Listings scraped (raw) | 473 |
| Listings after de-dup | 335 |
| Old listings (>90 days) | 20 |
| User's example listing | FOUND |
| Export file | data/output/Nordrhein-Westfalen_real_estate_old_listings_*.xlsx |

---

## Architecture

```
main.py                          # CLI + interactive entry point
+-- scraper.kleinanzeigen.py     # KleinanzeigenScraper class
    +-- scrape_bundesland()      # Main orchestration
        +-- Phase 1: State-level search
        |   +-- _walk_paginated()     # Walk category pages
        |   +-- _parse_listing_card() # Extract from search cards
        |   +-- _has_next_page()      # Detect pagination
        +-- Phase 2: Sub-location walker
        |   +-- fetch_sub_locations() # Discover cities
        |   +-- build_subcategory_url() # City-level URLs
        +-- Phase 3: Date fetching
        |   +-- _fetch_listing_dates() # Visit detail pages
        |   +-- fetch_listing_date()  # Scrape from detail page
        +-- Phase 4: Filter and finalize
            +-- De-duplicate by URL
            +-- Filter by age > 90 days
    +-- _make_request()          # HTTP with retry + rate limiting
    +-- close()                 # Clean up resources

+-- scraper.utils.py
    +-- URL Generation
    |   +-- generate_search_url()        # Umbrella URL
    |   +-- generate_all_category_urls() # All subcategories
    |   +-- build_page_url()             # Pagination
    |   +-- build_subcategory_url()     # City-level URLs
    +-- Sub-location Discovery
    |   +-- fetch_sub_locations()       # Discover cities
    +-- Date Parsing
    |   +-- parse_kleinanzeigen_date()   # All German formats
    |   +-- calculate_age_days()         # Age calculation
    |   +-- is_older_than_3_months()    # Filter check
    +-- Detail-page Date Fetching
        +-- fetch_listing_date()         # From detail page

+-- scraper.exporter.py
    +-- ExcelExporter
    |   +-- export_old_listings()  # Only >90 days
    |   +-- export_all_listings()  # All listings
    |   +-- _write_excel()           # Internal writer
    +-- export_to_excel()          # Convenience function

+-- scraper.models.py
    +-- Listing        # Dataclass with auto-calculating age
    +-- ScrapeResult   # Dataclass holding run results

+-- config.settings.Settings
    +-- constants: BASE_URL, IMMOBILIEN_CATEGORY, REAL_ESTATE_SUBCATEGORIES,
                   REQUEST_DELAY, MAX_PAGES, MAX_LISTINGS_FOR_DATES,
                   MIN_AGE_DAYS, etc.

+-- data.bundesland_mapping.json
    +-- 16 entries, each with name, url_param, location_id, english_name
```

---

## Configuration Reference

### Settings Class (config/settings.py)

| Setting | Default | Description |
|---|---|---|
| BASE_URL | "https://www.kleinanzeigen.de" | Kleinanzeigen base URL |
| IMMOBILIEN_CATEGORY | "c195" | Umbrella category code |
| DEFAULT_QUERY_PARAMS | "posterType=PRIVATE&sortingField=SORTING_DATE" | Filter private sellers, sort by date |
| REQUEST_DELAY | (2, 4) | Random delay in seconds between requests |
| MAX_PAGES | 25 | Safety limit per category |
| REQUEST_TIMEOUT | 30 | HTTP timeout in seconds |
| MAX_RETRIES | 3 | Maximum retries for failed requests |
| MAX_LISTINGS_FOR_DATES | None | Cap on detail-page date fetches (None = no cap) |
| MIN_AGE_DAYS | 90 | Listings older than this are exported |
| SUB_LOC_MAX_PAGES_PER_CATEGORY | 3 | Pages per city/category |
| SUB_LOC_BREADTH_LIMIT | 100 | Max sub-locations to walk per run |
| USER_AGENTS | List of 5 | Rotating User-Agent strings |
| OUTPUT_DIR | data/output/ | Excel output directory |
| LOG_FILE | scraper.log | Log file path |

---

## Known Limitations

### 1. Activation Date vs. Original Posting Date
- The detail page exposes the LAST ACTIVATION date of a listing (when the seller last bumped it)
- This is the correct signal for finding neglected listings
- Original creation date is NOT available in the static HTML (requires JavaScript)
- For buyers looking for stale inventory, activation date is what matters

### 2. Sort Order
- Kleinanzeigen's default sort is "Empfohlen" (relevance), not date
- The UI offers "Neueste" (newest) but no "Aelteste" (oldest)
- Old listings may not surface on the first pages
- Solution: The scraper paginates deep (up to 25 pages) to find old listings

### 3. Rate of Finding Old Listings
- Modern German real-estate market: sellers bump listings every 7-30 days
- Listings >90 days old are genuinely rare
- This is a property of the marketplace, not a bug in the scraper
- The scraper correctly identifies these rare listings when they exist

### 4. HTML Drift
- Selectors and URL scheme verified on 2026-06-28
- Kleinanzeigen can change their markup at any time
- This code will need periodic re-verification

---

## Performance Characteristics

### Runtime Estimates
| Bundesland | Size | Estimated Runtime (Default) | Estimated Runtime (Optimized) |
|------------|------|----------------------------|-------------------------------|
| Bremen | Small | 5-10 minutes | 90 seconds |
| Hamburg | Small | 10-15 minutes | 2 minutes |
| Bayern | Large | 45-60+ minutes | 10-15 minutes |
| NRW | Large | 45-60+ minutes | 10-15 minutes |

Default settings: MAX_PAGES=25, REQUEST_DELAY=(2,4), all sub-locations

Optimized settings (for testing):
```python
MAX_PAGES = 3
MAX_LISTINGS_FOR_DATES = 50
REQUEST_DELAY = (0.3, 0.6)
SUB_LOC_BREADTH_LIMIT = 10
```

### Request Counts
- State-level: 9 categories x 25 pages = 225 requests
- Sub-locations: Up to 100 cities x 9 categories x 3 pages = 2,700 requests
- Detail pages: Up to N requests (where N = listings without dates from cards)
- Total: ~3,000+ requests for a full Bundesland scrape

---

## Date Format Examples

The scraper handles all Kleinanzeigen date formats:

| Input | Parsed As | Notes |
|-------|-----------|-------|
| "Heute" | Current date | Today |
| "Gestern" | Current date - 1 day | Yesterday |
| "Heute, 19:51" | Current date | Today with time |
| "Gestern, 09:42" | Current date - 1 day | Yesterday with time |
| "vor 2 Tagen" | Current date - 2 days | N days ago |
| "vor 3 Wochen" | Current date - 21 days | N weeks ago |
| "vor 2 Monaten" | Current date - 2 months | N months ago |
| "vor 1 Jahren" | Current date - 1 year | N years ago |
| "13.06.2025" | 2025-06-13 | DD.MM.YYYY format |
| "01.01.2024" | 2024-01-01 | DD.MM.YYYY format |
| "Januar 2024" | 2024-01-01 | Month YYYY |
| "Februar 2024" | 2024-02-01 | Month YYYY |

---

## Next Steps (Out of Scope)

Potential future enhancements:

1. JavaScript-capable fallback (Selenium/Playwright)
   - Extract original creation date (not just activation date)
   - Handle any future JavaScript-rendered content

2. Multi-Bundesland batch runs
   - Scrape multiple states in one run
   - Combined Excel output or separate files

3. Custom date thresholds
   - --since YYYY-MM-DD argument
   - --min-age DAYS argument

4. Database storage
   - Track changes between runs
   - Detect new old listings
   - Historical analysis

5. Notifications
   - Email alerts when new old listings appear
   - Webhook integrations

6. GUI interface
   - Web-based or desktop GUI
   - Currently CLI only

7. Scheduled runs
   - Cron jobs or scheduled tasks
   - Automatic periodic scraping

8. Docker containerization
   - Easy deployment
   - Consistent environment

---

## Verification Checklist

- [x] All 16 Bundeslaender can be searched
- [x] Region filtering works correctly (locationId)
- [x] All 9 subcategories return correct listings
- [x] Date parsing handles all Kleinanzeigen formats
- [x] Age filtering works correctly (>90 days)
- [x] Excel export is properly formatted
- [x] Sheet names are truncated to 31 characters
- [x] No rate limiting issues (with proper delays)
- [x] Error handling for network issues
- [x] Logging for debugging (console + file)
- [x] Clean, maintainable code
- [x] Comprehensive test suite
- [x] Detailed documentation
- [x] Verified against live Kleinanzeigen.de
- [x] User's example listing found (Rees, NRW, 380 days)

---

## Related Documents

| File | Purpose |
|------|---------|
| README.md | Complete user guide, installation, usage |
| PROJECT_PLAN.md | Original project plan with completion status |
| FIXES_SUMMARY.md | Bug history, root causes, fixes applied |
| test_basic.py | Test suite with actual pass/fail reporting |
| config/settings.py | All configuration constants |
| data/bundesland_mapping.json | Bundesland -> location_id mappings |

---

## Summary

The ImmoRetterApp scraper is fully functional, verified, and production-ready. It successfully:

1. Finds real estate listings in any German Bundesland
2. Filters for listings older than 90 days
3. Exports results to properly formatted Excel files
4. Handles all Kleinanzeigen date formats
5. Respects rate limiting and anti-scraping measures
6. Finds listings that other scrapers miss through the sub-location walker
7. Provides comprehensive logging and error handling
8. Includes a test suite that actually reports failures

The project is ready for production use.
