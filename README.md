# Kleinanzeigen.de Real Estate Scraper

A Python application that scrapes Kleinanzeigen.de for real estate listings in German Bundeslaender, filters for listings older than 3 months, and exports the results to Excel.

## Prerequisites

### Linux (Ubuntu/Debian)

Before installing Python dependencies, you need to install system libraries for `lxml`:

```bash
sudo apt-get update
sudo apt-get install -y libxml2-dev libxslt1-dev python3-dev zlib1g-dev
```

### Windows

On Windows, `lxml` can be installed directly via pip without additional system dependencies:

```cmd
pip install lxml
```

If you encounter issues, try using pre-built wheels:

```cmd
pip install --only-binary :all: lxml
```

### macOS

```bash
# Using Homebrew
brew install libxml2 libxslt
brew link libxml2 --force
brew link libxslt --force
```

## Quick Start

```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Linux/macOS
venv\Scripts\activate     # On Windows

# Install dependencies
pip install -r requirements.txt

# List available Bundeslaender
python main.py --list

# Scrape a specific Bundesland
python main.py --bundesland "Bayern"

# Scrape and export ALL listings (not just old ones)
python main.py --bundesland "Bayern" --all

# Run in interactive mode
python main.py --interactive
```

## Alternative: Install without lxml

If you cannot install `lxml`, you can use Python's built-in HTML parser instead:

```bash
# Install dependencies without lxml
pip install requests beautifulsoup4 pandas openpyxl python-dateutil

# The scraper will automatically fall back to html.parser
python main.py --bundesland "Bayern"
```

**Note**: The built-in `html.parser` is slower than `lxml` and may have slightly different parsing behavior, but it will work for most cases.

## Step-by-Step Execution Process

When you run the scraper with `python main.py --bundesland "Nordrhein-Westfalen"`, here's what happens:

### Phase 1: Initialization
1. **Load Configuration**: Reads settings from `config/settings.py`
2. **Validate Bundesland**: Checks if the provided Bundesland name is valid using `data/bundesland_mapping.json`
3. **Setup Logging**: Initializes logging to both console and `scraper.log` file
4. **Create Session**: Sets up HTTP session with random user agent and headers

### Phase 2: Category Setup
5. **Generate Category URLs**: Creates search URLs for all 8 real estate subcategories:
   - `c198` - Gewerbeimmobilien (Commercial real estate)
   - `c199` - Wohnungen (Apartments)
   - `c200` - Haeuser (Houses)
   - `c201` - Zimmer (Rooms)
   - `c202` - WG (Shared apartments)
   - `c203` - Grundstuecke (Plots of land)
   - `c204` - Garagen/Stellplaetze (Garages/parking spaces)
   - `c205` - Ferienwohnungen (Vacation homes)

### Phase 3: Scraping Search Results
6. **Fetch Search Pages**: For each category, the scraper:
   - Requests the search results page from Kleinanzeigen.de
   - Waits 1-3 seconds between requests (rate limiting)
   - Parses the HTML response using BeautifulSoup
   - Extracts all listing cards from the page

7. **Extract Listing Information**: For each listing found:
   - Extracts title from the listing card
   - Extracts URL (link to the detail page)
   - Extracts price (if available)
   - Extracts location
   - **Note**: Posting date is NOT extracted here (not available in search results)

8. **Pagination Handling**: The scraper continues to the next page if:
   - A "next page" link is found in the HTML, OR
   - The current page number is less than MAX_PAGES (50)
   - Not all listings with dates are newer than 3 months

### Phase 4: Date Fetching
9. **Fetch Detail Pages**: After scraping all search results, the scraper:
   - Visits each listing's detail page
   - Extracts the posting date from the detail page HTML
   - Parses the date string (e.g., "28.11.2022") into a datetime object
   - Calculates the age in days from the current date

10. **Determine Old Listings**: For each listing:
    - If age > 90 days: marked as "older than 3 months"
    - Otherwise: marked as new

### Phase 5: Export Results
11. **Filter Old Listings**: Creates a list of only the old listings
12. **Generate Excel File**: Exports the results to an Excel file with columns:
    - Title
    - URL
    - Price
    - Location
    - Date Posted
    - Age (Days)
    - Older than 3 months (Yes/No)

13. **Display Summary**: Prints a summary to the console:
    - Total listings found
    - Number of old listings found
    - Number of pages scraped
    - Duration of the scraping process
    - Path to the exported Excel file

### Phase 6: Cleanup
14. **Close Session**: Properly closes the HTTP session
15. **Exit**: Program completes

**Total Process**: The scraper typically processes 200-500+ listings across all categories and pages, fetching dates for each one, and finally exports the filtered results.

## Features

- Scrape real estate listings from Kleinanzeigen.de
- Support for all 16 German Bundeslaender
- Filter listings older than 3 months (90 days)
- Export results to Excel with proper formatting
- Robust date parsing for various Kleinanzeigen formats
- Automatic date fetching from listing detail pages
- Rate limiting to avoid being blocked
- Comprehensive error handling and logging
- CLI and interactive modes
- Works with or without lxml parser

## Project Structure

```
kleinanzeigen-scraper/
├── main.py                          # Main entry point
├── README.md                        # This file
├── PROJECT_PLAN.md                  # Detailed project plan
├── IMPLEMENTATION_SUMMARY.md        # Implementation status
├── FIXES_SUMMARY.md                 # Summary of fixes applied
├── requirements.txt                 # Dependencies
├── .env.example                     # Environment template
├── .gitignore                       # Git ignore patterns
├── test_basic.py                    # Basic tests
├── config/
│   └── settings.py                  # Configuration
├── scraper/
│   ├── __init__.py
│   ├── models.py                    # Data models
│   ├── utils.py                     # Utility functions
│   ├── kleinanzeigen.py             # Core scraping logic
│   └── exporter.py                  # Excel export
└── data/
    ├── bundesland_mapping.json      # Bundesland to URL mapping
    └── output/                      # Excel files output
```

## Documentation

- [PROJECT_PLAN.md](PROJECT_PLAN.md) - Detailed project planning
- [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) - Implementation status and next steps
- [FIXES_SUMMARY.md](FIXES_SUMMARY.md) - Complete summary of all fixes applied

## Troubleshooting

### "Couldn't find a tree builder with the features you requested: lxml"

This error occurs when `lxml` is not installed. Solutions:

1. **Install lxml** (recommended for best performance):
   ```bash
   pip install lxml
   ```

2. **Install system dependencies** (Linux only):
   ```bash
   sudo apt-get install libxml2-dev libxslt1-dev python3-dev
   pip install lxml
   ```

3. **Use built-in parser** (no installation needed):
   - The code will automatically fall back to `html.parser` if `lxml` is not available
   - No additional installation required

### Rate Limited / Blocked

If you're being rate limited:
- Increase the delay between requests by modifying `REQUEST_DELAY` in `config/settings.py`
- Use a VPN or proxy
- Try again later

### No Results Found

If no old listings are found:
- Try a different Bundesland
- Check if there are actually old listings on Kleinanzeigen.de for that region
- The scraper only finds listings that are explicitly older than 90 days
- Note: In test environments, the system date might be in the future (e.g., 2026), so no listings will appear old

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

This project is open source and available under the [MIT License](LICENSE).

---

**Note**: This tool is for educational and personal use only. Web scraping may violate Kleinanzeigen.de's terms of service. Use responsibly and respect their servers.
