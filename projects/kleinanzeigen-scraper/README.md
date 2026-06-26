# Kleinanzeigen.de Real Estate Scraper

A Python application that scrapes Kleinanzeigen.de for real estate listings in a specified Bundesland, filters for listings older than 3 months, and exports the links to an Excel file.

## ⚠️ Important Legal Notice

**Before using this scraper, please be aware of the following:**

1. **Terms of Service**: Web scraping may violate Kleinanzeigen.de's terms of service. Use at your own risk.
2. **Rate Limiting**: This scraper includes rate limiting to avoid overloading their servers.
3. **Respect robots.txt**: The scraper respects robots.txt directives.
4. **Personal Use**: This tool is intended for personal, non-commercial use only.

## 🎯 Features

- ✅ Scrape real estate listings from Kleinanzeigen.de
- ✅ Filter listings older than 3 months (90 days)
- ✅ Support for all 16 German Bundesländer
- ✅ Export results to Excel with proper formatting
- ✅ Robust date parsing for various Kleinanzeigen date formats
- ✅ Rate limiting to avoid being blocked
- ✅ Error handling and retry logic
- ✅ Comprehensive logging
- ✅ CLI and interactive modes

## 📦 Installation

### Prerequisites

- Python 3.10 or higher
- pip (Python package manager)

### Setup

```bash
# Clone or download the repository
git clone <repository-url>
cd kleinanzeigen-scraper

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## 🚀 Usage

### Command Line Interface

```bash
# List available Bundesländer
python main.py --list

# Scrape a specific Bundesland
python main.py --bundesland "Bayern"

# Scrape and export ALL listings (not just old ones)
python main.py --bundesland "Nordrhein-Westfalen" --all

# Verbose mode (more logging)
python main.py --bundesland "Berlin" --verbose

# Interactive mode
python main.py --interactive
python main.py -i
```

### Examples

```bash
# Scrape Bayern and export old listings
python main.py -b "Bayern"

# Scrape Hamburg and export all listings
python main.py -b "Hamburg" --all

# List all available Bundesländer
python main.py -l
```

## 📁 Project Structure

```
kleinanzeigen-scraper/
├── main.py                  # Main entry point
├── scraper/
│   ├── __init__.py
│   ├── kleinanzeigen.py     # Core scraping logic
│   ├── models.py            # Data models
│   ├── utils.py             # Helper functions
│   └── exporter.py          # Excel export functionality
├── config/
│   └── settings.py          # Configuration
├── data/
│   ├── bundesland_mapping.json  # Bundesland to URL mapping
│   └── output/              # Excel files output
├── requirements.txt         # Dependencies
├── .env.example             # Environment template
└── README.md
```

## 🎛️ Configuration

### Settings

You can modify the scraping behavior in `config/settings.py`:

```python
class Settings:
    # Request configuration
    REQUEST_DELAY = (2, 5)  # Random delay between requests in seconds
    MAX_PAGES = 100  # Maximum pages to scrape
    MAX_RETRIES = 3  # Maximum retries for failed requests
    
    # Date filtering
    MIN_AGE_DAYS = 90  # Listings older than this will be included
    
    # Output
    OUTPUT_DIR = "data/output"  # Where to save Excel files
```

### Environment Variables

Create a `.env` file based on `.env.example`:

```bash
cp .env.example .env
```

## 📊 Output Format

The scraper creates Excel files with the following columns:

| Column | Description |
|--------|-------------|
| Title | Title of the listing |
| URL | Full URL to the listing |
| Price | Price (if available) |
| Location | Location of the property |
| Date Posted | Original date string from Kleinanzeigen |
| Age (Days) | Calculated age in days |
| Older than 3 months | Yes/No |

Additionally, a "Summary" sheet is included with:
- Bundesland
- Total listings found
- Old listings (>3 months)
- Pages scraped
- Duration
- Number of errors

## 🔧 Supported Bundesländer

All 16 German federal states are supported:

1. Baden-Württemberg
2. Bayern
3. Berlin
4. Brandenburg
5. Bremen
6. Hamburg
7. Hessen
8. Mecklenburg-Vorpommern
9. Niedersachsen
10. Nordrhein-Westfalen
11. Rheinland-Pfalz
12. Saarland
13. Sachsen
14. Sachsen-Anhalt
15. Schleswig-Holstein
16. Thüringen

## 🛠️ Technical Details

### Date Parsing

The scraper handles various date formats used by Kleinanzeigen:

- "Heute" (Today)
- "Gestern" (Yesterday)
- "vor 2 Tagen" (2 days ago)
- "vor 3 Wochen" (3 weeks ago)
- "vor 2 Monaten" (2 months ago)
- "01.01.2024" (DD.MM.YYYY)
- "Januar 2024" (Month Year)

### Pagination

- Automatically handles pagination
- Stops when no more results are available
- Stops early if all listings on a page are newer than 3 months (optimization)
- Respects maximum page limit for safety

### Rate Limiting

- Random delays between requests (2-5 seconds by default)
- User-Agent rotation
- Exponential backoff for failed requests
- Respects HTTP 429 (Too Many Requests) responses

## 🐛 Troubleshooting

### Common Issues

**1. No listings found**
- Check if the Bundesland name is spelled correctly
- Try with `--verbose` flag to see detailed logs
- Kleinanzeigen might have changed their HTML structure

**2. Rate limiting / Blocking**
- Increase `REQUEST_DELAY` in settings
- Try again later
- Use a VPN or proxy if needed

**3. CAPTCHA**
- Kleinanzeigen may show CAPTCHA for automated requests
- Try reducing the scraping speed
- Consider using selenium instead of requests

**4. Excel export issues**
- Ensure you have write permissions in the output directory
- Check that openpyxl is installed: `pip install openpyxl`

### Debug Mode

Enable verbose logging to see detailed information:

```bash
python main.py -b "Bayern" --verbose
```

This will show:
- Each URL being requested
- Parsing details
- Errors and warnings
- Timing information

## 📝 Logging

Logs are saved to `scraper.log` in the project root directory.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

## 🙏 Acknowledgments

- Inspired by the need for better real estate market analysis tools
- Built with Python and beautiful libraries like requests, BeautifulSoup, and pandas

---

**Disclaimer**: This tool is for educational and personal use only. The authors are not responsible for any misuse or violation of Kleinanzeigen.de's terms of service.
