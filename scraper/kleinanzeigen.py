"""
Main scraping logic for Kleinanzeigen.de
"""

import time
import random
import logging
from typing import Optional, List
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from requests.exceptions import RequestException

from .models import Listing, ScrapeResult
from .utils import (
    get_parser,
    parse_kleinanzeigen_date,
    get_random_user_agent,
    generate_all_category_urls,
    fetch_listing_date,
)
from config.settings import Settings

# Set up logging
logger = logging.getLogger(__name__)


class KleinanzeigenScraper:
    """Main scraper class for Kleinanzeigen.de"""
    
    def __init__(self):
        self.session = requests.Session()
        self.settings = Settings()
        self._setup_session()
    
    def _setup_session(self):
        """Configure the requests session"""
        self.session.headers.update(Settings.DEFAULT_HEADERS)
        self.session.headers.update({"User-Agent": get_random_user_agent()})
    
    def _get_random_delay(self) -> float:
        """Get a random delay between requests"""
        return random.uniform(*self.settings.REQUEST_DELAY)
    
    def _make_request(self, url: str, max_retries: int = None) -> Optional[str]:
        """
        Make HTTP request with retries and rate limiting
        
        Args:
            url: URL to request
            max_retries: Maximum number of retries (defaults to settings)
        
        Returns:
            HTML content or None if failed
        """
        if max_retries is None:
            max_retries = self.settings.MAX_RETRIES
        
        for attempt in range(max_retries + 1):
            try:
                # Random delay before request
                delay = self._get_random_delay()
                logger.debug(f"Waiting {delay:.2f} seconds before request to {url}")
                time.sleep(delay)
                
                # Rotate user agent occasionally
                if attempt > 0:
                    self.session.headers.update({"User-Agent": get_random_user_agent()})
                
                response = self.session.get(
                    url,
                    timeout=self.settings.REQUEST_TIMEOUT
                )
                
                # Check for successful response
                if response.status_code == 200:
                    return response.text
                elif response.status_code == 429:
                    # Rate limited - wait longer
                    wait_time = 2 ** attempt * 5  # Exponential backoff
                    logger.warning(f"Rate limited. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                elif response.status_code == 404:
                    logger.warning(f"Page not found: {url}")
                    return None
                else:
                    logger.warning(f"HTTP {response.status_code}: {url}")
                    
            except RequestException as e:
                logger.warning(f"Request failed (attempt {attempt + 1}/{max_retries + 1}): {e}")
                if attempt < max_retries:
                    time.sleep(2 ** attempt)  # Exponential backoff
        
        logger.error(f"Failed to fetch {url} after {max_retries + 1} attempts")
        return None
    
    def _parse_listing_card(self, card: BeautifulSoup) -> Optional[Listing]:
        """
        Parse a single listing card from search results
        
        Args:
            card: BeautifulSoup element representing a listing card
        
        Returns:
            Listing object or None if parsing fails
        """
        try:
            # Extract title
            title_element = card.select_one("[data-testid='ad-title']")
            if not title_element:
                title_element = card.select_one("h2 a")
            title = title_element.get_text(strip=True) if title_element else ""
            
            # Extract URL
            url = None
            if title_element and title_element.has_attr("href"):
                url = title_element["href"]
                # Make absolute URL if relative
                if url and not url.startswith("http"):
                    url = f"{self.settings.BASE_URL}{url}"
            
            # If no URL found, try other selectors
            if not url:
                link_element = card.select_one("a[href*='/s-anzeige/']")
                if link_element and link_element.has_attr("href"):
                    url = link_element["href"]
                    if not url.startswith("http"):
                        url = f"{self.settings.BASE_URL}{url}"
            
            # Try data-href attribute (used in modern Kleinanzeigen)
            if not url:
                url = card.get("data-href")
                if url and not url.startswith("http"):
                    url = f"{self.settings.BASE_URL}{url}"
            
            if not url:
                logger.debug("Could not extract URL from listing card")
                return None
            
            # Extract price
            price_element = card.select_one("[data-testid='ad-price']")
            if not price_element:
                price_element = card.select_one(".price")
            if not price_element:
                price_element = card.select_one(".aditem-main--middle--price-shipping--price")
            price = price_element.get_text(strip=True) if price_element else None
            
            # Extract location
            location_element = card.select_one("[data-testid='ad-location']")
            if not location_element:
                location_element = card.select_one(".location")
            if not location_element:
                location_element = card.select_one(".aditem-main--top--left")
            if location_element:
                # Clean up location text (remove icons, etc.)
                location = location_element.get_text(strip=True)
                # Remove location icon text if present
                location = location.replace("\u200b", "").strip()
            else:
                location = None
            
            # Extract date - dates are not in the search results HTML (loaded via JS)
            # We'll set date_posted to None initially and fetch it from the detail page later
            date_posted = None
            date_parsed = None
            
            # Try to extract from card anyway (might work for some layouts)
            date_element = card.select_one("[data-testid='ad-date']")
            if not date_element:
                date_element = card.select_one(".date")
            if not date_element:
                # Look for calendar icon followed by date
                calendar_icon = card.select_one("i.icon-calendar")
                if calendar_icon:
                    # Get next sibling or parent's text
                    parent = calendar_icon.parent
                    if parent:
                        text = parent.get_text(strip=True)
                        # Try to find a date in the text
                        import re
                        date_match = re.search(r'(Heute|Gestern|vor \d+ (Tagen|Wochen|Monaten|Jahren)|\d{1,2}\.\d{1,2}\.\d{4})', text)
                        if date_match:
                            date_posted = date_match.group(1)
            
            if date_posted:
                date_parsed = parse_kleinanzeigen_date(date_posted)
            
            listing = Listing(
                title=title,
                url=url,
                price=price,
                location=location,
                date_posted=date_posted,
                date_parsed=date_parsed,
            )
            
            return listing
            
        except Exception as e:
            logger.error(f"Error parsing listing card: {e}")
            return None
    
    def _fetch_listing_dates(self, listings: List[Listing]) -> List[Listing]:
        """
        Fetch posting dates from listing detail pages for listings that don't have dates
        
        Args:
            listings: List of Listing objects
        
        Returns:
            Updated list of Listing objects with dates fetched
        """
        updated_listings = []
        
        for i, listing in enumerate(listings):
            # If we already have a date, skip
            if listing.date_posted or listing.date_parsed:
                updated_listings.append(listing)
                continue
            
            # Fetch date from detail page
            date_str = fetch_listing_date(listing.url, self.session)
            
            if date_str:
                date_parsed = parse_kleinanzeigen_date(date_str)
                # Create a new listing with the date
                listing = Listing(
                    title=listing.title,
                    url=listing.url,
                    price=listing.price,
                    location=listing.location,
                    date_posted=date_str,
                    date_parsed=date_parsed,
                )
            
            updated_listings.append(listing)
            
            # Log progress every 10 listings
            if (i + 1) % 10 == 0:
                logger.info(f"Fetched dates for {i + 1}/{len(listings)} listings...")
            
            # Small delay between requests
            time.sleep(0.3)
        
        return updated_listings
    
    def _extract_listings_from_page(self, html: str) -> List[Listing]:
        """
        Extract all listings from a search results page
        
        Args:
            html: HTML content of search results page
        
        Returns:
            List of Listing objects
        """
        listings = []
        
        try:
            soup = BeautifulSoup(html, get_parser())
            
            # Find all listing cards - try different selectors
            # Modern Kleinanzeigen uses specific data-testid attributes
            card_selectors = [
                "[data-testid='ad-item']",  # Modern
                ".aditem",  # Older
                "article",  # Generic
                ".ad-listitem",  # Alternative
            ]
            
            cards = []
            for selector in card_selectors:
                cards = soup.select(selector)
                if cards:
                    break
            
            if not cards:
                # Try to find any elements that might be listing cards
                cards = soup.select("div[class*='ad']")
            
            logger.debug(f"Found {len(cards)} potential listing cards")
            
            for card in cards:
                listing = self._parse_listing_card(card)
                if listing:
                    listings.append(listing)
            
        except Exception as e:
            logger.error(f"Error extracting listings from page: {e}")
        
        return listings
    
    def _has_next_page(self, html: str, current_page: int) -> bool:
        """
        Check if there's a next page of results
        
        Args:
            html: HTML content of current page
            current_page: Current page number
        
        Returns:
            True if next page exists
        """
        try:
            soup = BeautifulSoup(html, get_parser())
            
            # Look for next page link - Kleinanzeigen uses different formats
            next_selectors = [
                "a[rel='next']",
                "[data-testid='pagination-next']",
                ".pagination-next",
                "a[title='Nächste']",
                "a[title='Weiter']",
            ]
            
            for selector in next_selectors:
                next_link = soup.select_one(selector)
                if next_link:
                    return True
            
            # Check if current page is less than max pages
            if current_page < self.settings.MAX_PAGES:
                # Try to find page number links
                # Kleinanzeigen uses different pagination formats:
                # 1. /s-.../seite:2/...
                # 2. ?o=2
                page_links = soup.select("a[href*='seite:']")
                for link in page_links:
                    href = link.get("href", "")
                    # Extract page number from /seite:N/ format
                    if "seite:" in href:
                        try:
                            page_num = int(href.split("seite:")[1].split("/")[0])
                            if page_num > current_page:
                                return True
                        except ValueError:
                            pass
                
                # Also check for ?o=N format
                page_links = soup.select("a[href*='o=']")
                for link in page_links:
                    href = link.get("href", "")
                    # Extract page number from URL
                    if "o=" in href:
                        try:
                            page_num = int(href.split("o=")[1].split("&")[0])
                            if page_num > current_page:
                                return True
                        except ValueError:
                            pass
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking for next page: {e}")
            return False
    
    def _should_continue_pagination(self, listings: List[Listing], has_next_page: bool) -> bool:
        """
        Determine if we should continue to the next page
        
        We stop pagination when:
        1. We've reached the max pages limit
        2. There's no next page
        3. We have enough listings with dates and all are newer than 3 months
           (since results are sorted by date, newest first)
        
        Args:
            listings: Listings from current page
            has_next_page: Whether there's a next page available
        
        Returns:
            True if we should continue
        """
        if not listings:
            return False
        
        # If there's no next page, stop
        if not has_next_page:
            return False
        
        # If we have listings with dates and all are newer than 3 months, stop
        listings_with_dates = [l for l in listings if l.date_parsed]
        
        if listings_with_dates:
            all_new = all(
                not listing.is_older_than_3_months 
                for listing in listings_with_dates
            )
            
            if all_new:
                logger.info("All listings on page with dates are newer than 3 months. Stopping pagination.")
                return False
        
        # Otherwise, continue
        return True
    
    def scrape_bundesland(self, bundesland: str, bundesland_url_param: str) -> ScrapeResult:
        """
        Scrape all real estate listings for a Bundesland
        
        Args:
            bundesland: Name of the Bundesland
            bundesland_url_param: URL parameter for the Bundesland
        
        Returns:
            ScrapeResult object
        """
        result = ScrapeResult(
            bundesland=bundesland,
            start_time=datetime.now(),
        )
        
        logger.info(f"Starting scrape for {bundesland}...")
        
        # Generate all category URLs
        category_urls = generate_all_category_urls(bundesland_url_param)
        logger.info(f"Scraping {len(category_urls)} real estate categories...")
        
        # Scrape each category
        for cat_url in category_urls:
            page = 1
            while page <= self.settings.MAX_PAGES:
                # Generate URL for current page
                if page == 1:
                    url = cat_url
                else:
                    # Try to use the same pagination format as the first page
                    # If the first page URL has /seite:1/, use /seite:N/
                    # Otherwise, use ?o=N
                    if "/seite:" in cat_url:
                        # Replace /seite:1/ with /seite:N/
                        url = cat_url.replace("/seite:1/", f"/seite:{page}/")
                    else:
                        url = f"{cat_url}?o={page}" if "?" not in cat_url else f"{cat_url}&o={page}"
                
                logger.info(f"Scraping page {page} of category {cat_url.split('/')[-1]}: {url}")
                
                # Fetch the page
                html = self._make_request(url)
                if html is None:
                    result.errors.append(f"Failed to fetch page {page} of {cat_url}")
                    break
                
                # Extract listings from page
                listings = self._extract_listings_from_page(html)
                result.listings.extend(listings)
                result.total_listings_found += len(listings)
                result.pages_scraped = page
                
                logger.info(f"Found {len(listings)} listings on page {page} of {cat_url.split('/')[-1]}")
                
                # Check if there's a next page
                has_next_page = self._has_next_page(html, page)
                
                # Check if we should continue
                if not self._should_continue_pagination(listings, has_next_page):
                    break
                
                page += 1
        
        # Fetch dates for listings that don't have them
        logger.info(f"Fetching dates for {len(result.listings)} listings...")
        result.listings = self._fetch_listing_dates(result.listings)
        
        # Filter for old listings
        old_listings = result.get_old_listings()
        result.old_listings_found = len(old_listings)
        
        result.end_time = datetime.now()
        
        logger.info(
            f"Completed scrape for {bundesland}: "
            f"{result.total_listings_found} total, "
            f"{result.old_listings_found} older than 3 months, "
            f"{result.pages_scraped} pages in {result.duration_seconds:.1f}s"
        )
        
        return result
    
    def close(self):
        """Clean up resources"""
        self.session.close()


def scrape_kleinanzeigen(bundesland: str, bundesland_url_param: str) -> ScrapeResult:
    """
    Convenience function to scrape Kleinanzeigen for a Bundesland
    
    Args:
        bundesland: Name of the Bundesland
        bundesland_url_param: URL parameter for the Bundesland
    
    Returns:
        ScrapeResult object
    """
    scraper = KleinanzeigenScraper()
    try:
        return scraper.scrape_bundesland(bundesland, bundesland_url_param)
    finally:
        scraper.close()
