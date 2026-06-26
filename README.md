# Kleinanzeigen.de Real Estate Scraper

A Python application that scrapes Kleinanzeigen.de for real estate listings in German Bundesländer, filters for listings older than 3 months, and exports the results to Excel.

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# List available Bundesländer
python main.py --list

# Scrape a specific Bundesland
python main.py --bundesland "Bayern"

# Run in interactive mode
python main.py --interactive
```

## 📋 Features

- ✅ Scrape real estate listings from Kleinanzeigen.de
- ✅ Support for all 16 German Bundesländer
- ✅ Filter listings older than 3 months (90 days)
- ✅ Export results to Excel with proper formatting
- ✅ Robust date parsing for various Kleinanzeigen formats
- ✅ Rate limiting to avoid being blocked
- ✅ Comprehensive error handling and logging
- ✅ CLI and interactive modes

## 📁 Project Structure

```
kleinanzeigen-scraper/
├── main.py                          # Main entry point
├── README.md                        # This file
├── PROJECT_PLAN.md                  # Detailed project plan
├── IMPLEMENTATION_SUMMARY.md        # Implementation status
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

## 📖 Documentation

- [PROJECT_PLAN.md](PROJECT_PLAN.md) - Detailed project planning
- [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) - Implementation status and next steps

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

---

**Note**: This tool is for educational and personal use only. Web scraping may violate Kleinanzeigen.de's terms of service. Use responsibly and respect their servers.
