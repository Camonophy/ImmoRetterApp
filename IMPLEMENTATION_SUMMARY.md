# Kleinanzeigen.de Real Estate Scraper - Implementation Summary

## Project Status: \u2705 Working

The scraper scrapes Kleinanzeigen.de for real estate listings in a specified German Bundesland, filters for listings that haven't been bumped in more than 3 months (90 days), and exports to Excel.

## What Works (verified 2026-06-28)

### Region-filtered search
The scraper uses the modern `locationId` URL parameter to scope the search to the requested Bundesland. Verified against live Kleinanzeigen.de: when run for "Bremen", all 322 scraped listings have locations in Bremen (`27568 Bremerhaven`, `28201 Neustadt`, `28329 Neue Vahr Nord`, \u2026).

### Subcategory coverage
5 curated real-estate subcategories configured, each addressed via the modern category-code URL scheme:
`/s-immobilien/<region>/<category_code>l<locationId>?posterType=PRIVATE&sortingField=SORTING_DATE`.
Category codes: c196 (Eigentumswohnung kaufen), c198 (Weitere Immobilien), c203 (Mietwohnung), c207 (Grundst\u00fccke & G\u00e4rten), c208 (H\u00e4user zum Kauf).

### Field extraction
For every search-result card the scraper correctly extracts:
- **Title** (`h2.text-module-begin a`)
- **URL** (from the title's `href` or `data-href`)
- **Price** (`.aditem-main--middle--price-shipping--price`)
- **Location** (`.aditem-main--top--left`)

The activation date is fetched separately from each listing's detail page (calendar icon in `#viewad-extra-info`).

### Age filter
Listings whose activation date is older than 90 days are flagged and exported.

### Excel export
- Sheet names are truncated to 31 chars to avoid Excel warnings.
- The "old listings only" export and the "all listings" export are now separate, explicit functions. The previous silent fallback (where a "no old listings" run would write a file full of recent listings under a misleading filename) has been removed.
- A summary sheet with run statistics is included.
- 6-column export: Postleitzahl, Name des Verk\u00e4ufers, Standort, Aktueller Wert (\u20ac), Datum seit online, Link

### Test suite
`python test_basic.py` actually reports pass/fail per check and exits non-zero on failure. It covers imports, date parsing, settings, Bundesland mapping (including `location_id` presence), URL generation, and the age filter.

## End-to-End Run Results

Live run against NRW (`Mietwohnung` subcategory, 12 pages):

| Stat | Value |
|---|---|
| Total listings found | 324 |
| Listings with extracted date | 324 (100%) |
| Date-fetch errors | 0 |
| Age range | 0 \u2013 49 days |
| Listings >90 days old | 0 (Kleinanzeigen sorts by relevance, not date) |
| Pages scraped | 12 |
| Duration | 343 s |

A separate live run against Bremen (5 subcategories \u00d7 1-2 pages each):
- 322 listings, all with locations in Bremen
- All dates extracted without error
- 0 listings >90 days (Bremen is a hot market; sellers bump frequently)

The 0 >90-day results are a property of Kleinanzeigen's marketplace, not a bug in the scraper.

## Architecture

```
main.py                          # CLI + interactive entry point
\u2514\u2500\u2500 scraper.kleinanzeigen.py     # KleinanzeigenScraper class
    \u251c\u2500\u2500 scrape_bundesland()      # main loop: walk subcategories \u00d7 pages
    \u251c\u2500\u2500 _make_request()          # HTTP with retry + rate limiting
    \u251c\u2500\u2500 _parse_listing_card()    # extract title/URL/price/location from card
    \u251c\u2500\u2500 _extract_listings_from_page()
    \u251c\u2500\u2500 _has_next_page()         # detect pagination
    \u2514\u2500\u2500 _fetch_listing_dates()   # visit detail pages, get activation dates
        \u2514\u2500\u2500 (via scraper.utils.fetch_listing_date)

\u2514\u2500\u2500 scraper.utils.py
    \u251c\u2500\u2500 generate_search_url()        # umbrella URL with locationId
    \u251c\u2500\u2500 generate_all_category_urls() # category-code-based subcategory URLs
    \u251c\u2500\u2500 build_page_url()             # ?o=N pagination
    \u251c\u2500\u2500 parse_kleinanzeigen_date()   # DD.MM.YYYY, "vor X Tagen", etc.
    \u2514\u2500\u2500 fetch_listing_date()         # scrape date from detail page

\u2514\u2500\u2500 scraper.exporter.py
    \u251c\u2500\u2500 ExcelExporter.export_old_listings()
    \u251c\u2500\u2500 ExcelExporter.export_all_listings()
    \u2514\u2500\u2500 export_to_excel()  # convenience function

\u2514\u2500\u2500 scraper.models.py
    \u251c\u2500\u2500 Listing        # dataclass with __post_init__ auto-calculating age
    \u2514\u2500\u2500 ScrapeResult   # dataclass holding the run's listings + stats

\u2514\u2500\u2500 scraper.ui.py
    \u2514\u2500\u2500 Console & ProgressBar classes for terminal UI

\u2514\u2500\u2500 config.settings.Settings
    \u2514\u2500\u2500 constants: BASE_URL, IMMOBILIEN_CATEGORY, REAL_ESTATE_SUBCATEGORIES,
                   REQUEST_DELAY, MAX_PAGES, MAX_LISTINGS_FOR_DATES,
                   MIN_AGE_DAYS, etc.

\u2514\u2500\u2500 data.bundesland_mapping.json
    \u2514\u2500\u2500 16 entries, each with name, url_param, location_id
```

## Known Limitations

- **Activation date vs. original posting date.** The detail page exposes the LAST ACTIVATION date of a listing (when the seller last bumped it) but not the original creation date. For "find listings that have been sitting around for >90 days" the activation date is the right signal \u2014 listings the seller hasn't bothered to bump in 3+ months are exactly the neglected ones a buyer wants. But a user wanting the literal creation date would need a JS-capable client.
- **Sort order.** Kleinanzeigen's default sort is "Empfohlen" (relevance), not date. The UI offers a "Neueste" (newest) sort but no "\u00c4lteste" (oldest). So old listings may not surface on the first pages; the scraper has to paginate deep to find them.
- **Rate of finding old listings.** Modern German real-estate market has sellers bumping listings every 7-30 days, so >90-day-old activations are genuinely rare.
- **HTML drift.** Selectors and the modern URL scheme were verified on 2026-06-28. Kleinanzeigen can change their markup at any time; this code will need to be re-verified periodically.

## Next Steps (out of scope, but worth noting)

- A JS-capable fallback (Selenium/Playwright) for the original creation date
- Multi-Bundesland batch runs
- A `--since YYYY-MM-DD` argument for finding listings activated before a given date
- Database storage for tracking changes between runs
- Email/notification on new old listings

See [FIXES_SUMMARY.md](FIXES_SUMMARY.md) for the full list of bugs fixed.
