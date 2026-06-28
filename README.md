# Kleinanzeigen.de Real Estate Scraper - ImmoRetter

A Python application that scrapes Kleinanzeigen.de for real estate listings in a German Bundesland, filters for listings that haven't been bumped in more than 3 months (90 days), and exports the results to Excel.

> **Status**: ✅ **Production Ready** - Verified against live Kleinanzeigen.de (2026-06-28)

---

## 🎯 What It Does

**ImmoRetter** helps you find **neglected real estate listings** on Kleinanzeigen.de - properties that sellers haven't refreshed in over 90 days. These are often:
- Better deals (motivated sellers)
- Long-standing properties that other buyers have overlooked
- Unique opportunities in competitive markets

### Key Features
- ✅ **Region-filtered search** across all 16 German Bundesländer
- ✅ **9 real estate subcategories** (Mietwohnung, Wohnung, Haus, Eigentumswohnung, etc.)
- ✅ **Accurate region scoping** using Kleinanzeigen's `locationId` parameter
- ✅ **Private seller focus** (filters out commercial/agency listings)
- ✅ **Activation date extraction** from listing detail pages
- ✅ **Robust date parsing** for all German date formats
- ✅ **Two-phase search strategy** (state-level + sub-location/city-level)
- ✅ **De-duplication** of listings across search phases
- ✅ **Excel export** with summary statistics
- ✅ **Rate limiting** with random delays (2-4s) and rotating user agents
- ✅ **Comprehensive error handling** with retry logic
- ✅ **CLI and interactive modes**
- ✅ **Test suite** with real pass/fail reporting

---

## 📋 Quick Start

### Prerequisites

#### Linux (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install -y libxml2-dev libxslt1-dev python3-dev zlib1g-dev
```

#### Windows
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
# List available Bundesländer
python main.py --list

# Scrape a specific Bundesland for old listings (>90 days)
python main.py --bundesland "Bayern"

# Scrape and export ALL listings (not just old ones)
python main.py --bundesland "Bayern" --all

# Run in interactive mode
python main.py --interactive

# Run with verbose logging
python main.py --bundesland "Nordrhein-Westfalen" --verbose

# Run the test suite
python test_basic.py
```

---

## 🔍 How It Works

When you run `python main.py --bundesland "Nordrhein-Westfalen"`, the scraper performs the following steps:

### Phase 1: Initialization
1. **Load Configuration**: Reads settings from `config/settings.py` and the Bundesland → locationId mapping from `data/bundesland_mapping.json`
2. **Validate Bundesland**: Looks up the requested Bundesland's `url_param` and **`location_id`** (a numeric ID that Kleinanzeigen uses internally to scope searches to a state)
3. **Setup Logging**: Initializes logging to console and `scraper.log`
4. **Create Session**: Sets up an HTTP session with rotating User-Agent

### Phase 2: Build Search URLs
For each configured subcategory (9 in total), the scraper builds a region-filtered URL:
```
https://www.kleinanzeigen.de/s-immobilien/<region>/<category_code>l<locationId>?posterType=PRIVATE&sortingField=SORTING_DATE
```

**Category Codes:**
- `c195` - Immobilien (umbrella)
- `c196` - Eigentumswohnung kaufen
- `c197` - Garage & Lagerraum
- `c198` - Weitere Immobilien
- `c199` - Auf Zeit & WG
- `c203` - Mietwohnung
- `c205` - Häuser zur Miete
- `c207` - Grundstücke & Gärten
- `c208` - Häuser zum Kauf

### Phase 3: Paginate and Scrape Search Results
For each subcategory, the scraper walks through pages (up to 25 by default) and extracts from each result card:
- **Title** (`<h2 class="text-module-begin"><a>`)
- **URL** (from the title's `href` or the `data-href` attribute)
- **Price** (`<p class="aditem-main--middle--price-shipping--price">`)
- **Location** (`<div class="aditem-main--top--left">`)
- **Activation Date** (from `<div class="aditem-main--top--right">` when available)

### Phase 4: Sub-Location Walker
After the state-level search, the scraper:
1. Discovers all cities/sub-regions within the Bundesland from the sidebar
2. For each sub-location (capped at 100), walks all categories
3. De-duplicates listings by URL (same listing may appear in both state and city searches)

This is **critical** because Kleinanzeigen's state-level pagination is limited (~3 pages), while city-level searches paginate completely and surface listings that would otherwise be missed.

### Phase 5: Fetch Activation Dates
For listings without dates from search cards, the scraper visits the detail page and extracts the activation date from:
```html
<div id="viewad-extra-info" class="boxedarticle--details--full">
  <div>
    <i class="icon icon-small icon-calendar-gray-simple"></i>
    <span>24.06.2026</span>  <!-- Last activation date -->
  </div>
</div>
```

**Important**: This is the **last activation date** (when the seller last bumped the listing), not the original posting date. For finding neglected listings, this is the correct signal.

### Phase 6: Filter and Export
- Filter listings where `age_days > 90` (configurable via `MIN_AGE_DAYS` in settings)
- Export to `<output_dir>/<Bundesland>_real_estate_old_listings_<timestamp>.xlsx`
- Excel file contains:
  - **Main sheet**: All filtered listings (or all listings if `--all` flag used)
  - **Summary sheet**: Run statistics (total found, old listings, pages scraped, duration, errors)

**Columns in Excel export:**
| Title | URL | Price | Location | Date Posted | Age (Days) | Older than 3 months |

If no listings match the age filter, the script prints a clear message and does NOT create a misleading file.

---

## 📊 Supported Bundesländer

All 16 German federal states are supported:

| Bundesland | URL Param | Location ID |
|------------|-----------|-------------|
| Baden-Württemberg | baden-wuerttemberg | 7970 |
| Bayern | bayern | 5510 |
| Berlin | berlin | 3331 |
| Brandenburg | brandenburg | 7711 |
| Bremen | bremen | 1 |
| Hamburg | hamburg | 9409 |
| Hessen | hessen | 4279 |
| Mecklenburg-Vorpommern | mecklenburg-vorpommern | 61 |
| Niedersachsen | niedersachsen | 2428 |
| Nordrhein-Westfalen | nordrhein-westfalen | 928 |
| Rheinland-Pfalz | rheinland-pfalz | 4938 |
| Saarland | saarland | 285 |
| Sachsen | sachsen | 3799 |
| Sachsen-Anhalt | sachsen-anhalt | 2165 |
| Schleswig-Holstein | schleswig-holstein | 408 |
| Thüringen | thueringen | 3548 |

---

## ⚙️ Configuration

Edit `config/settings.py` to customize the scraper behavior:

| Setting | Default | Description |
|---------|---------|-------------|
| `REQUEST_DELAY` | `(2, 4)` | Random delay in seconds between requests |
| `MAX_PAGES` | `25` | Max pages scraped per subcategory (safety limit) |
| `REQUEST_TIMEOUT` | `30` | HTTP timeout in seconds |
| `MAX_RETRIES` | `3` | HTTP retries on transient errors |
| `MAX_LISTINGS_FOR_DATES` | `None` | Optional cap on detail-page date fetches (None = no cap) |
| `MIN_AGE_DAYS` | `90` | Listings older than this will be exported |
| `SUB_LOC_MAX_PAGES_PER_CATEGORY` | `3` | Max pages per category when walking sub-locations |
| `SUB_LOC_BREADTH_LIMIT` | `100` | Max sub-locations to walk per run |

### Tuning for Faster Runs

A full scrape of one Bundesland with default settings can take 30-60+ minutes. For quick experimentation:

```python
# In config/settings.py
MAX_PAGES = 3                       # only 3 pages per subcategory
MAX_LISTINGS_FOR_DATES = 50         # cap detail-page date fetches at 50
REQUEST_DELAY = (0.3, 0.6)          # aggressive delay
```

With these settings, a run against Bremen completes in about 90 seconds.

---

## 📁 Project Structure

```
ImmoRetterApp/
├── main.py                          # Main entry point (CLI + interactive)
├── README.md                        # This file
├── requirements.txt                 # Dependencies
├── test_basic.py                    # Test suite
├── config/
│   └── settings.py                  # Configuration constants
├── scraper/
│   ├── __init__.py
│   ├── models.py                    # Data models (Listing, ScrapeResult)
│   ├── utils.py                     # URL generation, date parsing, helpers
│   ├── kleinanzeigen.py             # Core scraping logic
│   └── exporter.py                  # Excel export functionality
└── data/
    ├── bundesland_mapping.json      # Bundesland → url_param + location_id
    └── output/                      # Generated Excel files
```

---

## 🧪 Testing

Run the comprehensive test suite:
```bash
python test_basic.py
```

The test suite validates:
- ✅ All imports work correctly
- ✅ Date parsing for all German formats
- ✅ Settings configuration
- ✅ Bundesland mapping (all 16 states have locationIds)
- ✅ URL generation (modern format with locationId)
- ✅ Age filter calculation

**Note**: The test suite now actually reports failures. If you see ❌ markers, the corresponding functionality is broken.

---

## 🐛 Troubleshooting

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

Or let the scraper fall back to Python's built-in `html.parser`:
```bash
pip install requests beautifulsoup4 pandas openpyxl python-dateutil
```
The fallback is automatic; no code change needed.

### Rate Limited / Blocked
- Increase `REQUEST_DELAY` in `config/settings.py`
- Use a VPN or proxy
- Try again later
- Reduce `MAX_PAGES` to scrape fewer pages

### No Old Listings Found
- Try a different (larger) Bundesland — smaller ones like Bremen have very few stale listings
- Re-run with `--all` to inspect what came back
- Verify the search is region-filtered: check that the locationId is being used in URLs
- Note: In competitive markets, sellers bump listings frequently, so >90-day-old listings are genuinely rare

### Tests Fail
The test suite in `test_basic.py` reports failures with ❌ markers. If tests fail:
- Check that all dependencies are installed (`pip install -r requirements.txt`)
- Verify `data/bundesland_mapping.json` is valid JSON
- Ensure Python version is 3.10+

---

## 📈 Performance Notes

### Runtime Estimates
| Bundesland | Size | Estimated Runtime |
|------------|------|-------------------|
| Bremen | Small | 1-2 minutes |
| Hamburg | Medium | 5-10 minutes |
| Bayern | Large | 30-60+ minutes |
| Nordrhein-Westfalen | Largest | 45-90+ minutes |

**Note**: Runtime depends on:
- Number of listings in the region
- `MAX_PAGES` setting
- `REQUEST_DELAY` setting
- Whether sub-location walking is enabled

### Output Files
Excel files are saved to `data/output/` with the naming pattern:
```
{Bundesland}_real_estate_old_listings_{YYYY-MM-DD_HH-MM-SS}.xlsx
```

Each file contains:
- **Main sheet**: All filtered listings (or all if `--all` used)
- **Summary sheet**: Statistics about the scrape run

---

## 📚 Date Formats Handled

The scraper correctly parses all Kleinanzeigen date formats:
- "Heute" (Today)
- "Gestern" (Yesterday)
- "Heute, 19:51" (Today at 19:51)
- "Gestern, 09:42" (Yesterday at 09:42)
- "vor 2 Tagen" (2 days ago)
- "vor 3 Wochen" (3 weeks ago)
- "vor 2 Monaten" (2 months ago)
- "vor 1 Jahren" (1 year ago)
- "13.06.2025" (DD.MM.YYYY)
- "Januar 2024" (Month YYYY)

---

## 🔧 Dependencies

See `requirements.txt` for the complete list.

### Core Dependencies
- `requests` - HTTP client
- `beautifulsoup4` - HTML parsing
- `lxml` - Fast HTML parser (optional, falls back to html.parser)
- `pandas` - Data manipulation
- `openpyxl` - Excel export
- `python-dateutil` - Date parsing

### Optional Dependencies
- `selenium` - For JavaScript-rendered content (not currently used)
- `webdriver-manager` - Browser driver management
- `fake-useragent` - Additional user agent rotation
- `pytz` - Timezone handling
- `click` - CLI interface (not currently used)
- `tqdm` - Progress bars
- `colorlog` - Colored logging

---

## 📝 Recent Changes & Improvements

### Version History

#### Current Version (2026-06-28)
- ✅ **Fixed region filtering**: Added `locationId` to all Bundesland mappings
- ✅ **Fixed category codes**: Switched from slug-based to numeric category codes (c195-c208)
- ✅ **Added private seller filter**: `posterType=PRIVATE` in all search URLs
- ✅ **Added date-based sorting**: `sortingField=SORTING_DATE` for newest-first ordering
- ✅ **Implemented sub-location walker**: Discovers and scrapes all cities within a Bundesland
- ✅ **Improved date extraction**: Gets dates from search cards when available, falls back to detail pages
- ✅ **Fixed card selectors**: Updated to match modern Kleinanzeigen DOM
- ✅ **Fixed de-duplication**: Removes duplicate listings across state and city searches
- ✅ **Improved Excel export**: Separate functions for old vs. all listings, proper sheet name truncation
- ✅ **Enhanced test suite**: Now actually reports pass/fail for all checks
- ✅ **Better error handling**: Retries, timeouts, graceful degradation

See [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) and [FIXES_SUMMARY.md](FIXES_SUMMARY.md) for detailed information.

---

## ⚠️ Legal Disclaimer

**This tool is for educational and personal use only.**

- Web scraping may violate Kleinanzeigen.de's terms of service
- Use responsibly and respect their servers
- Do not use for commercial purposes without permission
- Do not overload their servers (rate limiting is built in)
- Consider contacting Kleinanzeigen for API access if you need reliable, high-volume data

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 Additional Documentation

- [PROJECT_PLAN.md](PROJECT_PLAN.md) - Original project plan (historical reference)
- [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) - Current implementation status
- [FIXES_SUMMARY.md](FIXES_SUMMARY.md) - Detailed bug fixes and solutions

---

## 📞 Support

For issues, questions, or suggestions:
- Check the [Troubleshooting](#-troubleshooting) section above
- Review the documentation files
- Open an issue on GitHub

---

**Happy scraping! 🏡**
