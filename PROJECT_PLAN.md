# Kleinanzeigen.de Real Estate Scraper - Project Plan

> ⚠️ **This document is the original project plan from 2024-08.** The actual current state of the project, the architecture that was implemented, and the bug history are documented in [README.md](README.md), [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) and [FIXES_SUMMARY.md](FIXES_SUMMARY.md). Kept here for historical reference only.

## 🎯 Project Overview

### Objective
Create a Python application that searches Kleinanzeigen.de for real estate offers in a specified Bundesland, filters for listings older than 3 months, and exports the links to an Excel file.

### Key Features
- User inputs a Bundesland (German federal state)
- Searches Kleinanzeigen.de for all real estate listings in that Bundesland
- Filters listings older than 3 months (90 days)
- Exports links to filtered listings in Excel format

## 🏗️ Technical Architecture

### Technology Stack
- **Language**: Python 3.10+
- **Web Scraping**: `requests` + `BeautifulSoup`, `selenium` (fallback)
- **Data Processing**: `pandas`
- **Excel Export**: `openpyxl`
- **Date Handling**: `datetime`, `dateutil`
- **Configuration**: `python-dotenv`
- **Logging**: `logging`

### Project Structure
```
kleinanzeigen-scraper/
├── main.py                  # Main entry point
├── scraper/
│   ├── __init__.py
│   ├── kleinanzeigen.py     # Core scraping logic
│   ├── models.py            # Data models
│   └── utils.py             # Helper functions
├── data/
│   ├── bundesland_mapping.json
│   └── output/
├── config/
│   └── settings.py
├── requirements.txt
├── .env.example
└── README.md
```

## 📋 Implementation Phases

### Phase 1: Setup & Configuration (Day 1)
- [ ] Create project directory structure
- [ ] Set up Python virtual environment
- [ ] Install dependencies (requirements.txt)
- [ ] Create Bundesland mapping configuration
- [ ] Set up logging configuration
- [ ] Create basic configuration system

### Phase 2: Core Scraping Logic (Day 2-3)
- [ ] Implement HTTP client with rate limiting
- [ ] Create search URL builder
- [ ] Implement search results page parser
- [ ] Extract listing metadata (title, URL, date, etc.)
- [ ] Handle pagination
- [ ] Implement error handling and retries

### Phase 3: Date Filtering (Day 4)
- [ ] Create date parser for Kleinanzeigen date formats
- [ ] Implement age calculation
- [ ] Create filtering logic (age > 90 days)
- [ ] Optimize: stop pagination when date threshold reached

### Phase 4: Data Export (Day 5)
- [ ] Create data model for listings
- [ ] Implement Excel export functionality
- [ ] Format Excel output (columns, headers, styling)
- [ ] Add timestamp to filename

### Phase 5: User Interface (Day 6)
- [ ] Create CLI interface
- [ ] Implement Bundesland selection
- [ ] Add progress feedback
- [ ] Create output directory if not exists

### Phase 6: Testing & Refinement (Day 7)
- [ ] Test with all Bundesländer
- [ ] Handle edge cases (no results, errors, etc.)
- [ ] Optimize performance
- [ ] Add comprehensive logging
- [ ] Create README with usage instructions

## 🎯 Key Technical Challenges

### 1. Date Parsing
Kleinanzeigen uses various date formats:
- "Heute" (Today)
- "Gestern" (Yesterday)  
- "vor 2 Tagen" (2 days ago)
- "vor 3 Wochen" (3 weeks ago)
- "vor 2 Monaten" (2 months ago)
- "01.01.2024" (DD.MM.YYYY)

**Solution**: Create a robust date parser that handles all formats.

### 2. Pagination
- Kleinanzeigen paginates results
- Need to detect when to stop (no more results or date threshold)
- Results are typically sorted by date (newest first)

**Solution**: Stop pagination when we encounter listings newer than 3 months (since we're going backwards in time).

### 3. Anti-Scraping Measures
- Rate limiting
- User-Agent detection
- CAPTCHA (potential issue)

**Solution**: 
- Random delays (2-5 seconds between requests)
- Rotate User-Agents
- Use session cookies
- Respect robots.txt

### 4. Dynamic Content
- Some content may be loaded via JavaScript

**Solution**: 
- Primary: Use requests + BeautifulSoup (faster)
- Fallback: Use selenium for dynamic content

## 📊 Data Model

### Listing Model
```python
@dataclass
class Listing:
    title: str
    url: str
    price: Optional[str]
    location: Optional[str]
    date_posted: str
    date_parsed: datetime
    age_days: int
    is_older_than_3_months: bool
```

### Output Excel Structure
| Title | URL | Price | Location | Date Posted | Age (Days) |
|-------|-----|-------|----------|-------------|------------|
| ... | ... | ... | ... | ... | ... |

## 🔧 Configuration

### settings.py
```python
class Settings:
    BASE_URL = "https://www.kleinanzeigen.de"
    SEARCH_PATH = "/s-immobilien/{region}/k0"
    REQUEST_DELAY = (2, 5)  # Random delay in seconds
    MAX_PAGES = 100  # Safety limit
    USER_AGENTS = [...]  # List of user agents
    OUTPUT_DIR = "data/output"
```

### bundesland_mapping.json
```json
{
  "Baden-Württemberg": "baden-wuerttemberg",
  "Bayern": "bayern",
  "Berlin": "berlin",
  "Brandenburg": "brandenburg",
  "Bremen": "bremen",
  "Hamburg": "hamburg",
  "Hessen": "hessen",
  "Mecklenburg-Vorpommern": "mecklenburg-vorpommern",
  "Niedersachsen": "niedersachsen",
  "Nordrhein-Westfalen": "nordrhein-westfalen",
  "Rheinland-Pfalz": "rheinland-pfalz",
  "Saarland": "saarland",
  "Sachsen": "sachsen",
  "Sachsen-Anhalt": "sachsen-anhalt",
  "Schleswig-Holstein": "schleswig-holstein",
  "Thüringen": "thueringen"
}
```

## ⚠️ Legal & Ethical Considerations

### Robots.txt
- Check https://www.kleinanzeigen.de/robots.txt
- Respect Crawl-delay if specified
- Don't scrape if disallowed

### Terms of Service
- Review Kleinanzeigen's terms
- Don't overload their servers
- Consider contacting them for API access

### Rate Limiting
- Maximum 1 request every 2-5 seconds
- No parallel requests
- Use delays between pages

## 📦 Dependencies

### requirements.txt
```
requests==2.31.0
beautifulsoup4==4.12.2
lxml==4.9.3
pandas==2.1.4
openpyxl==3.1.2
python-dateutil==2.8.2
python-dotenv==1.0.0
selenium==4.15.2
webdriver-manager==4.0.0
fake-useragent==1.4.0
```

## 🚀 Usage Example

```bash
# Install dependencies
pip install -r requirements.txt

# Run the scraper
python main.py --bundesland "Bayern"

# Output
# Scraping real estate listings for Bayern...
# Found 150 listings, 45 older than 3 months
# Saved to: data/output/bayern_real_estate_old_listings_2024-01-15.xlsx
```

## 📈 Success Metrics

- [ ] All 16 Bundesländer can be searched
- [ ] Date filtering works correctly
- [ ] Excel output is properly formatted
- [ ] No rate limiting issues
- [ ] Error handling for network issues
- [ ] Logging for debugging
- [ ] Clean, maintainable code

## 🔄 Next Steps

1. **Confirm**: Review and approve this plan
2. **Refine**: Any adjustments to requirements?
3. **Start**: Begin with Phase 1 implementation

## ❓ Open Questions

1. Should we include additional filters (price range, property type)?
2. Should we scrape additional details from each listing page?
3. Should we implement email notifications when new old listings appear?
4. Should we create a GUI or stick with CLI?
5. Should we add database storage for historical data?

## 📝 Notes

- Kleinanzeigen may have CAPTCHA for automated requests
- Consider using proxies if blocking occurs
- May need to handle JavaScript-rendered content with selenium
- Test with a small Bundesland first (e.g., Bremen, Saarland)
