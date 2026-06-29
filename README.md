# ImmoRetterApp - Kleinanzeigen.de Real Estate Scraper

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

**ImmoRetterApp** is a Python application that scrapes **Kleinanzeigen.de** for real estate listings in German Bundeslaender (federal states), filters for listings that haven't been bumped in more than 3 months (90+ days), and exports the results to Excel.

These "neglected" listings often represent better deals or more motivated sellers who haven't refreshed their ads recently.

---

## Features

### Core Functionality
- Search across all 16 German Bundeslaender
- 9 real estate subcategories (Houses, Apartments, Garages, etc.)
- Modern URL scheme with locationId for proper region scoping
- Activation date extraction from listing detail pages
- Sub-location walker to find listings in cities that don't surface in state-level searches
- Proper handling of German relative date strings ("Heute", "vor 2 Monaten", etc.)

### Output
- Excel export with Title, URL, Price, Location, Date Posted, Age (Days), Older than 3 months flag
- Summary sheet with per-run statistics
- Sheet names automatically truncated to Excel's 31-character limit
- Timestamped filenames for easy organization

### Anti-Scraping
- Random delay between requests (configurable: 2-4 seconds default)
- Rotating User-Agent strings
- HTTP retries on transient errors (3 attempts default)
- Respectful rate limiting

### Configuration
- Configurable via config/settings.py
- All 16 Bundeslaender with verified location_id mappings
- Adjustable page limits, timeouts, and delays

---

## Quick Start

### Prerequisites

#### Linux (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install -y libxml2-dev libxslt1-dev python3-dev zlib1g-dev
```

#### Windows
On Windows, lxml can be installed directly via pip:
```cmd
pip install lxml
```
If you encounter issues:
```cmd
pip install --only-binary :all: lxml
```

#### macOS
```bash
brew install libxml2 libxslt
brew link libxml2 --force
brew link libxslt --force
```

### Installation

```bash
# Clone the repository
git clone https://github.com/Camonophy/ImmoRetterApp.git
cd ImmoRetterApp

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Linux/macOS
venv\Scripts\activate     # On Windows

# Install dependencies
pip install -r requirements.txt
```

### Usage

```bash
# List available Bundeslaender
python main.py --list

# Scrape a specific Bundesland for old listings (>90 days)
python main.py --bundesland "Bayern"

# Scrape and export ALL listings (not just old ones)
python main.py --bundesland "Nordrhein-Westfalen" --all

# Run in interactive mode
python main.py --interactive

# Enable verbose logging
python main.py --bundesland "Bremen" --verbose

# Run the test suite
python test_basic.py
```

---

## What the Scraper Actually Does

When you run `python main.py --bundesland "Nordrhein-Westfalen"`, the scraper executes a two-phase search strategy:

### Phase 1: State-Level Search
1. **Load Configuration**: Reads settings from config/settings.py and Bundesland mappings from data/bundesland_mapping.json
2. **Validate Bundesland**: Looks up the requested Bundesland's url_param and location_id (critical for region filtering)
3. **Setup**: Initializes logging to console and scraper.log, creates HTTP session with rotating User-Agent
4. **Build URLs**: For each of 9 real estate subcategories, builds region-filtered URLs like:
   ```
   https://www.kleinanzeigen.de/s-immobilien/nordrhein-westfalen/c208l928?posterType=PRIVATE&sortingField=SORTING_DATE
   ```
   - c208: Category code (Hauser zum Kauf)
   - l928: Location ID that scopes the search to Nordrhein-Westfalen
   - posterType=PRIVATE: Filters out commercial listings (agencies)
   - sortingField=SORTING_DATE: Sorts by newest activation first
5. **Paginate**: Walks through pages (up to 25 per category by default)
6. **Extract**: From each result card, extracts Title, URL, Price, Location, and (when available) activation date

### Phase 2: Sub-Location Walker (Critical for Completeness)
This is what makes the scraper find listings that others miss:

1. **Discover Cities**: Fetches the sidebar from the state-level search page to discover all cities/sub-locations within the Bundesland
2. **City-Level Searches**: For each city (up to 100 by default), walks all 9 subcategories
3. **Find Hidden Listings**: Many listings only appear in city-level searches, not state-level pagination

**Example**: A user's example listing in Rees, NRW (locationId 1387) with activation date 13.06.2025 (380 days old) is only found via the sub-location walker.

### Phase 3: Date Fetching
For listings without dates from search cards:
1. Visits each listing's detail page
2. Extracts the activation date from the #viewad-extra-info section (calendar icon)
3. Parses the date using comprehensive German date format handling

### Phase 4: Filter and Export
1. **De-duplicate**: Removes duplicate listings (same URL appearing in multiple categories)
2. **Filter**: Keeps only listings with age_days > 90
3. **Export**: Writes to Excel with proper formatting and summary statistics

---

## Supported Real Estate Categories

The scraper searches across 9 subcategories using Kleinanzeigen's modern numeric category codes:

| Code | Category | English Translation |
|------|----------|-------------------|
| c195 | Immobilien | Real Estate (umbrella) |
| c196 | Eigentumswohnung kaufen | Condominiums for Sale |
| c197 | Garage & Lagerraum | Garages & Storage |
| c198 | Weitere Immobilien | Other Real Estate |
| c199 | Auf Zeit & WG | Temporary & Shared Housing |
| c203 | Mietwohnung | Apartments for Rent |
| c205 | Haeuser zur Miete | Houses for Rent |
| c207 | Grundstuecke & Gaerten | Plots & Gardens |
| c208 | Haeuser zum Kauf | Houses for Sale |

---

## Supported Bundeslaender

All 16 German federal states are supported with verified location IDs:

| Bundesland | location_id | English Name |
|------------|-------------|--------------|
| Baden-Wuerttemberg | 7970 | Baden-Wuerttemberg |
| Bayern | 5510 | Bavaria |
| Berlin | 3331 | Berlin |
| Brandenburg | 7711 | Brandenburg |
| Bremen | 1 | Bremen |
| Hamburg | 9409 | Hamburg |
| Hessen | 4279 | Hesse |
| Mecklenburg-Vorpommern | 61 | Mecklenburg-Vorpommern |
| Niedersachsen | 2428 | Lower Saxony |
| Nordrhein-Westfalen | 928 | North Rhine-Westphalia |
| Rheinland-Pfalz | 4938 | Rhineland-Palatinate |
| Saarland | 285 | Saarland |
| Sachsen | 3799 | Saxony |
| Sachsen-Anhalt | 2165 | Saxony-Anhalt |
| Schleswig-Holstein | 408 | Schleswig-Holstein |
| Thueringen | 3548 | Thuringia |

---

## Configuration

Edit config/settings.py to customize the scraper's behavior:

### Performance Settings
```python
REQUEST_DELAY = (2, 4)        # Random delay in seconds between requests
MAX_PAGES = 25                 # Max pages per category (safety limit)
REQUEST_TIMEOUT = 30          # HTTP timeout in seconds
MAX_RETRIES = 3               # Maximum retries for failed requests
```

### Scraping Limits
```python
MAX_LISTINGS_FOR_DATES = None  # Cap on detail-page date fetches (None = no cap)
SUB_LOC_MAX_PAGES_PER_CATEGORY = 3  # Pages per city/category
SUB_LOC_BREADTH_LIMIT = 100    # Max sub-locations to walk per run
```

### Filtering
```python
MIN_AGE_DAYS = 90  # Listings older than this are exported
```

### Tuning for Faster Runs
A full scrape of one Bundesland with default settings can take 30-60+ minutes. For quick testing:

```python
# In config/settings.py:
MAX_PAGES = 3                       # Only 3 pages per subcategory
MAX_LISTINGS_FOR_DATES = 50         # Cap detail-page date fetches at 50
REQUEST_DELAY = (0.3, 0.6)          # Aggressive delay (use with caution)
```

With these settings, a run against Bremen completes in about 90 seconds.

---

## Project Structure

```
ImmoRetterApp/
+-- main.py                          # Main entry point (CLI + interactive)
+-- README.md                        # This file
+-- requirements.txt                 # Dependencies
+-- test_basic.py                    # Test suite
+-- config/
|   +-- settings.py                  # Configuration constants
+-- scraper/
|   +-- __init__.py
|   +-- models.py                    # Data models (Listing, ScrapeResult)
|   +-- utils.py                     # URL generation, date parsing, fetching
|   +-- kleinanzeigen.py             # Core scraping logic (KleinanzeigenScraper)
|   +-- exporter.py                  # Excel export
+-- data/
    +-- bundesland_mapping.json      # Bundesland -> location_id mappings
    +-- output/                      # Generated Excel files
```

---

## Troubleshooting

### "Couldn't find a tree builder with the features you requested: lxml"

Either install lxml:
```bash
# Linux
sudo apt-get install -y libxml2-dev libxslt1-dev python3-dev zlib1g-dev
pip install lxml

# Windows
pip install --only-binary :all: lxml

# macOS
brew install libxml2 libxslt
brew link libxml2 --force
brew link libxslt --force
pip install lxml
```

Or let the scraper fall back to Python's built-in html.parser:
```bash
pip install requests beautifulsoup4 pandas openpyxl python-dateutil
```
The fallback is automatic - no code changes needed.

### Rate Limited / Blocked
- Increase REQUEST_DELAY in config/settings.py
- Use a VPN or proxy
- Try again later
- Reduce MAX_PAGES for testing

### No Old Listings Found
- Try a different (larger) Bundesland - smaller ones like Bremen have very few stale listings
- Re-run with --all to inspect what came back
- Verify the search is region-filtered: check that listings have locations in the requested Bundesland
- Note: In the current German real estate market, sellers typically bump listings every 7-30 days, so >90-day-old activations are genuinely rare

### Tests Fail
Run the test suite to verify your setup:
```bash
python test_basic.py
```
The test suite now actually reports failures. If you see failures:
- Check that all dependencies are installed
- Verify data/bundesland_mapping.json exists and is valid JSON
- Ensure Python 3.10+ is being used

---

## Data Models

### Listing
Represents a single Kleinanzeigen listing with:
- title: Listing title
- url: Full URL to the listing
- price: Price string (e.g., "65.000 EUR")
- location: Location string (e.g., "46459 Rees")
- date_posted: Raw date string from Kleinanzeigen
- date_parsed: Parsed datetime object
- age_days: Calculated age in days
- is_older_than_3_months: Boolean flag

### ScrapeResult
Represents the result of a scraping operation with:
- bundesland: Name of the Bundesland
- total_listings_found: Total listings discovered
- old_listings_found: Count of listings >90 days old
- listings: List of Listing objects
- pages_scraped: Total pages processed
- errors: List of error messages
- start_time / end_time: Timing information
- duration_seconds: Calculated duration

---

## Date Format Handling

The scraper handles all Kleinanzeigen date formats:

| Format | Example | Parsed As |
|--------|---------|-----------|
| Today | "Heute" | Current date |
| Yesterday | "Gestern" | Current date - 1 day |
| Days ago | "vor 2 Tagen" | Current date - N days |
| Weeks ago | "vor 3 Wochen" | Current date - N weeks |
| Months ago | "vor 2 Monaten" | Current date - N months |
| Years ago | "vor 1 Jahren" | Current date - N years |
| Absolute date | "13.06.2025" | DD.MM.YYYY |
| Month/Year | "Januar 2024" | First day of month |

---

## Verified Results

### End-to-End Test: Nordrhein-Westfalen
- Total listings found: 324 (Mietwohnung category, 12 pages)
- Listings with dates: 324 (100%)
- Date-fetch errors: 0
- Age range: 0-49 days
- Listings >90 days old: 0 (market reality, not a bug)
- Pages scraped: 12
- Duration: 343 seconds

### End-to-End Test: Bremen (All Categories)
- Total listings found: 322
- All locations in Bremen: Verified
- All dates extracted: Success
- Listings >90 days old: 0 (hot market)

### User Example Listing Test: Rees, NRW
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

---

## Contributing

1. Fork the repository
2. Create a feature branch (git checkout -b feature/amazing-feature)
3. Commit your changes (git commit -m 'Add amazing feature')
4. Push to the branch (git push origin feature/amazing-feature)
5. Open a Pull Request

---

## License

This project is for educational and personal use only. Web scraping may violate Kleinanzeigen.de's terms of service. Use responsibly and respect their servers.

---

## Links

- Repository: https://github.com/Camonophy/ImmoRetterApp
- Kleinanzeigen.de: https://www.kleinanzeigen.de
- Robots.txt: https://www.kleinanzeigen.de/robots.txt

---

## Version History

| Version | Date | Description |
|---------|------|-------------|
| 1.0 | 2026-06-28 | Initial working version with region filtering, sub-location walker, and comprehensive date parsing |
