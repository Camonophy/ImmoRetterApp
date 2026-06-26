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
    parse_kleinanzeigen_date,
    get_random_user_agent,
    generate_search_url,
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
            
            if not url:
                logger.debug("Could not extract URL from listing card")
                return None
            
            # Extract price
            price_element = card.select_one("[data-testid='ad-price']")
            if not price_element:
                price_element = card.select_one(".price")
            price = price_element.get_text(strip=True) if price_element else None
            
            # Extract location
            location_element = card.select_one("[data-testid='ad-location']")
            if not location_element:
                location_element = card.select_one(".location")
            location = location_element.get_text(strip=True) if location_element else None
            
            # Extract date - THIS IS CRITICAL FOR FILTERING
            date_element = card.select_one("[data-testid='ad-date']")
            if not date_element:
                # Try different selectors for date
                date_element = card.select_one(".date")
            if not date_element:
                date_element = card.select_one("small")
            if not date_element:
                date_element = card.select_one("span:last-child")
            
            date_posted = date_element.get_text(strip=True) if date_element else None
            
            # Parse date and create listing
            date_parsed = parse_kleinanzeigen_date(date_posted) if date_posted else None
            
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
            soup = BeautifulSoup(html, "lxml")
            
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
            soup = BeautifulSoup(html, "lxml")
            
            # Look for next page link
            next_selectors = [
                "a[rel='next']",
                "[data-testid='pagination-next']",
                ".pagination-next",
                "a:contains('Weiter')",
                "a:contains('Nächste')",
            ]
            
            for selector in next_selectors:
                next_link = soup.select_one(selector)
                if next_link:
                    return True
            
            # Check if current page is less than max pages
            if current_page < self.settings.MAX_PAGES:
                # Try to find page numbers and see if there's a higher one
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
    
    def _should_continue_pagination(self, listings: List[Listing]) -> bool:
        """
        Determine if we should continue to the next page
        
        We stop pagination when:
        1. We've reached the max pages limit
        2. All listings on the current page are newer than 3 months
           (since results are sorted by date, newest first)
        
        Args:
            listings: Listings from current page
        
        Returns:
            True if we should continue
        """
        if not listings:
            return False
        
        # If all listings are newer than 3 months, we can stop
        # (assuming results are sorted by date, newest first)
        all_new = all(
            not listing.is_older_than_3_months 
            for listing in listings 
            if listing.date_parsed
        )
        
        if all_new and len(listings) > 0:
            logger.info("All listings on page are newer than 3 months. Stopping pagination.")
            return False
        
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
        
        page = 1
        while page <= self.settings.MAX_PAGES:
            # Generate URL for current page
            url = generate_search_url(bundesland_url_param, page)
            logger.info(f"Scraping page {page}: {url}")
            
            # Fetch the page
            html = self._make_request(url)
            if html is None:
                result.errors.append(f"Failed to fetch page {page}")
                break
            
            # Extract listings from page
            listings = self._extract_listings_from_page(html)
            result.listings.extend(listings)
            result.total_listings_found += len(listings)
            result.pages_scraped = page
            
            logger.info(f"Found {len(listings)} listings on page {page}")
            
            # Check if we should continue
            if not self._should_continue_pagination(listings):
                break
            
            # Check if there's a next page
            if not self._has_next_page(html, page):
                logger.info("No more pages available")
                break
            
            page += 1
        
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
