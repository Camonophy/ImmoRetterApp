"""
Main scraping logic for Kleinanzeigen.de
"""

import time
import random
import re
import logging
from typing import Optional, List, Dict
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
    build_page_url,
    build_subcategory_url,
    fetch_sub_locations,
)
from config.settings import Settings


logger = logging.getLogger(__name__)


class KleinanzeigenScraper:
    """Main scraper class for Kleinanzeigen.de"""

    def __init__(self):
        self.session = requests.Session()
        self.settings = Settings()
        self._setup_session()

    # ------------------------------------------------------------------
    # Setup & low-level HTTP
    # ------------------------------------------------------------------
    def _setup_session(self):
        """Configure the requests session"""
        self.session.headers.update(self.settings.DEFAULT_HEADERS)
        self.session.headers.update({"User-Agent": get_random_user_agent()})

    def _get_random_delay(self) -> float:
        """Get a random delay between requests"""
        return random.uniform(*self.settings.REQUEST_DELAY)

    def _make_request(self, url: str, max_retries: Optional[int] = None) -> Optional[str]:
        """
        Make HTTP request with retries and rate limiting.

        Args:
            url: URL to request.
            max_retries: Maximum number of retries (defaults to settings).

        Returns:
            HTML content or None if failed.
        """
        if max_retries is None:
            max_retries = self.settings.MAX_RETRIES

        for attempt in range(max_retries + 1):
            try:
                delay = self._get_random_delay()
                logger.debug(f"Waiting {delay:.2f}s before request to {url}")
                time.sleep(delay)

                if attempt > 0:
                    self.session.headers.update({"User-Agent": get_random_user_agent()})

                response = self.session.get(url, timeout=self.settings.REQUEST_TIMEOUT)

                if response.status_code == 200:
                    return response.text
                if response.status_code == 429:
                    wait = 2 ** attempt * 5
                    logger.warning(f"Rate limited (429). Waiting {wait}s...")
                    time.sleep(wait)
                elif response.status_code == 404:
                    logger.warning(f"Page not found: {url}")
                    return None
                else:
                    logger.warning(f"HTTP {response.status_code}: {url}")

            except RequestException as e:
                logger.warning(f"Request failed (attempt {attempt + 1}/{max_retries + 1}): {e}")
                if attempt < max_retries:
                    time.sleep(2 ** attempt)

        logger.error(f"Failed to fetch {url} after {max_retries + 1} attempts")
        return None

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------
    def _parse_listing_card(self, card) -> Optional[Listing]:
        """
        Parse a single listing card from a search-results page.

        The current Kleinanzeigen DOM (verified 2026-06-28) uses these
        structural classes:
            <article class="aditem">
              <div class="aditem-main--top--left">  <!-- location -->
              <h2 class="text-module-begin">        <!-- title -->
                <a class="ellipsis" href="/s-anzeige/...">...</a>
              </h2>
              <p class="aditem-main--middle--price-shipping--price">  <!-- price -->
            </article>

        On sub-location search pages (e.g. c208l1387 for Rees) the card
        ALSO contains the activation date as a calendar-open icon followed
        by a date string in `.aditem-main--top--right`. On state-level pages
        the date is NOT in the card and must be fetched from the detail page.
        """
        try:
            # ---- URL (also gives us the title href) ----
            url = card.get("data-href")
            if not url:
                link = card.select_one("h2.text-module-begin a[href]") \
                       or card.select_one("a.ellipsis[href]") \
                       or card.select_one("a[href*='/s-anzeige/']")
                if link:
                    url = link.get("href")

            if not url:
                logger.debug("No URL on card, skipping")
                return None

            url = str(url)
            if not url.startswith("http"):
                url = f"{self.settings.BASE_URL}{url}"

            # ---- Title ----
            title_el = card.select_one("h2.text-module-begin a") \
                       or card.select_one("h2 a")
            title = title_el.get_text(strip=True) if title_el else ""

            # ---- Price ----
            price_el = card.select_one(".aditem-main--middle--price-shipping--price") \
                       or card.select_one("[class*='price-shipping--price']") \
                       or card.select_one(".price")
            price = price_el.get_text(" ", strip=True) if price_el else None
            if price:
                price = price.split("\n")[0].strip()

            # ---- Location ----
            loc_el = card.select_one(".aditem-main--top--left") \
                       or card.select_one("[class*='top--left']") \
                       or card.select_one(".location")
            location = loc_el.get_text(" ", strip=True) if loc_el else None
            if location:
                # Strip the unicode zero-width-space and any trailing
                # distance markers like "(6 km)" that Kleinanzeigen appends
                # for sub-location searches.
                location = location.replace("\u200b", "").strip()
                location = re.sub(r"\s*\(\d+\s*km\)\s*$", "", location).strip()
                # Collapse internal whitespace runs (from \n in the source).
                location = re.sub(r"\s+", " ", location)

            # ---- Activation date (present on every modern card) ----
            date_posted = None
            date_parsed = None
            date_right = card.select_one(".aditem-main--top--right")
            if date_right:
                text = date_right.get_text(" ", strip=True)
                # Two formats appear in the wild:
                #   - absolute: "13.06.2025" (sub-location cards)
                #   - relative: "Heute, 19:18" / "Gestern, 09:42" (state-level cards)
                # Both are accepted by parse_kleinanzeigen_date.
                # First try the absolute DD.MM.YYYY format (more precise).
                m = re.search(r"(\d{1,2}\.\d{1,2}\.\d{4})", text)
                if m:
                    date_posted = m.group(1)
                elif text:
                    # Fall back to the relative text (parse_kleinanzeigen_date
                    # handles "Heute", "Gestern", "vor X Tagen", etc.).
                    date_posted = text
                if date_posted:
                    date_parsed = parse_kleinanzeigen_date(date_posted)

            return Listing(
                title=title,
                url=url,
                price=price,
                location=location,
                date_posted=date_posted,
                date_parsed=date_parsed,
            )

        except Exception as e:
            logger.error(f"Error parsing listing card: {e}")
            return None

    def _extract_listings_from_page(self, html: str) -> List[Listing]:
        """Extract every listing card from one search-results HTML page."""
        listings: List[Listing] = []
        try:
            soup = BeautifulSoup(html, get_parser())
            # Try modern first, then fall back gracefully.
            cards = soup.select(".aditem")
            if not cards:
                cards = soup.select("article")
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
        Detect whether a 'next page' link exists.

        Looks for the modern `.pagination` block (with links of the form
        `/s-immobilien/<region>/seite:N/<cat>l<id>`) and for the legacy
        `?o=N` query string.
        """
        try:
            soup = BeautifulSoup(html, get_parser())

            # Modern pagination block
            pagination = soup.select_one(".pagination")
            if pagination:
                # Page numbers or a "next" arrow with a higher page number
                page_links = pagination.select("a[href*='seite:']")
                for link in page_links:
                    href = link.get("href", "")
                    m = re.search(r"/seite:(\d+)/", href)
                    if m and int(m.group(1)) > current_page:
                        return True
                # Next-arrow (› or "Weiter")
                for link in pagination.select("a"):
                    txt = link.get_text(strip=True) or ""
                    href = link.get("href", "") or ""
                    m = re.search(r"/seite:(\d+)/", href)
                    if m and int(m.group(1)) > current_page:
                        return True
                    if "seite:" in href and txt in (">", "›", "»", "Weiter", "Nächste", "Next"):
                        return True

            # Legacy ?o= style
            for link in soup.select("a[href*='o=']"):
                href = link.get("href", "") or ""
                m = re.search(r"[?&]o=(\d+)", href)
                if m and int(m.group(1)) > current_page:
                    return True

            return False
        except Exception as e:
            logger.error(f"Error checking for next page: {e}")
            return False

    # ------------------------------------------------------------------
    # Date fetching
    # ------------------------------------------------------------------
    def _fetch_listing_dates(self, listings: List[Listing]) -> List[Listing]:
        """
        Fetch activation dates for every listing that doesn't have one yet.

        Respects `MAX_LISTINGS_FOR_DATES` if set (None = no cap). Logs
        progress every 10 listings.
        """
        max_listings = self.settings.MAX_LISTINGS_FOR_DATES
        updated: List[Listing] = []
        processed = 0
        skipped = 0
        errors = 0

        for i, listing in enumerate(listings):
            if max_listings is not None and processed >= max_listings:
                logger.warning(
                    f"Reached MAX_LISTINGS_FOR_DATES cap of {max_listings}; "
                    f"{len(listings) - i} listings will not have dates fetched"
                )
                # Append the rest as-is so they're still in the export
                updated.extend(listings[i:])
                break

            if listing.date_parsed:
                updated.append(listing)
                skipped += 1
                continue

            date_str = fetch_listing_date(listing.url, self.session)
            processed += 1

            if date_str:
                date_parsed = parse_kleinanzeigen_date(date_str)
                updated.append(Listing(
                    title=listing.title,
                    url=listing.url,
                    price=listing.price,
                    location=listing.location,
                    date_posted=date_str,
                    date_parsed=date_parsed,
                ))
            else:
                # No date found; keep the listing but mark as not-old.
                updated.append(listing)
                errors += 1

            if processed % 10 == 0:
                logger.info(
                    f"Date fetch progress: {processed}/{len(listings)} "
                    f"(skipped={skipped}, errors={errors})"
                )

        logger.info(
            f"Date fetch complete: {processed} fetched, {skipped} already had "
            f"dates, {errors} returned no date"
        )
        return updated

    # ------------------------------------------------------------------
    # Top-level scraping
    # ------------------------------------------------------------------
    def scrape_bundesland(self, bundesland: str,
                          bundesland_url_param: str,
                          location_id: Optional[str] = None,
                          walk_sub_locations: bool = True) -> ScrapeResult:
        """
        Scrape all real estate listings for a Bundesland.

        Strategy:
          1. Walk the state-level search (locationId = state id) for every
             configured real-estate subcategory.
          2. ALSO walk every sub-location (city) inside the state. This is
             necessary because:
               - The state-level search shows ~3,000 private Häuser zum
                 Kauf listings in NRW, but the site only lets us paginate
                 ~3 pages deep before returning the same cards over and over.
               - The same listings ARE findable via the much smaller
                 per-city searches (each city has 0-100 listings, paginates
                 completely in 1-5 pages).
          3. De-duplicate by listing URL.

        Args:
            bundesland: Display name of the Bundesland (e.g. 'Bayern').
            bundesland_url_param: URL slug (e.g. 'bayern').
            location_id: Numeric Kleinanzeigen locationId from
                bundesland_mapping.json. REQUIRED for the region filter
                to work — without it, the search returns nationwide
                results. Falls back to nationwide if None.
            walk_sub_locations: If True, also walk every city-level search.
                Set to False for a quick state-only scan.

        Returns:
            ScrapeResult object.
        """
        result = ScrapeResult(
            bundesland=bundesland,
            start_time=datetime.now(),
        )

        if location_id:
            logger.info(f"Starting scrape for {bundesland} (region-filtered via locationId={location_id})")
        else:
            logger.warning(
                f"Starting scrape for {bundesland} WITHOUT locationId — "
                f"results will be nationwide, not region-filtered!"
            )

        # ----- Phase 1: state-level search -----
        category_urls = generate_all_category_urls(bundesland_url_param, location_id)
        logger.info(f"Phase 1: state-level search, {len(category_urls)} subcategories")
        for cat_url in category_urls:
            slug = cat_url.split("/s-immobilien/")[-1].split("?")[0]
            logger.info(f"--- Category: {slug} ---")
            self._walk_paginated(cat_url, result)

        # ----- Phase 2: sub-location walker -----
        if walk_sub_locations and location_id:
            sub_locs = fetch_sub_locations(bundesland_url_param, location_id,
                                          session=self.session)
            # Limit breadth to avoid runaway runtime for large states.
            if len(sub_locs) > self.settings.SUB_LOC_BREADTH_LIMIT:
                logger.warning(
                    f"Bundesland has {len(sub_locs)} sub-locations; "
                    f"capping at SUB_LOC_BREADTH_LIMIT={self.settings.SUB_LOC_BREADTH_LIMIT}"
                )
                sub_locs = sub_locs[:self.settings.SUB_LOC_BREADTH_LIMIT]
            logger.info(f"Phase 2: walking {len(sub_locs)} sub-locations inside {bundesland}")
            for sub in sub_locs:
                logger.info(f"--- Sub-location: {sub['name']} (id={sub['id']}) ---")
                for cat in Settings.REAL_ESTATE_SUBCATEGORIES:
                    sub_url = build_subcategory_url(cat["code"], sub["id"], page=1)
                    self._walk_paginated(sub_url, result,
                                         max_pages=self.settings.SUB_LOC_MAX_PAGES_PER_CATEGORY)

        # ----- Phase 3: fetch activation dates -----
        logger.info(f"Fetching activation dates for {len(result.listings)} listings...")
        result.listings = self._fetch_listing_dates(result.listings)

        # De-duplicate by URL (sub-location walker can re-find listings
        # already seen at state level).
        seen_urls = set()
        unique = []
        for listing in result.listings:
            key = listing.url
            if key in seen_urls:
                continue
            seen_urls.add(key)
            unique.append(listing)
        if len(unique) < len(result.listings):
            logger.info(f"De-duplicated {len(result.listings)} -> {len(unique)} unique listings")
            result.listings = unique
            result.total_listings_found = len(unique)

        # ----- Phase 4: filter and finalize -----
        old_listings = result.get_old_listings()
        result.old_listings_found = len(old_listings)
        result.end_time = datetime.now()

        logger.info(
            f"Done: {result.total_listings_found} unique listings, "
            f"{result.old_listings_found} older than {Settings.MIN_AGE_DAYS} days, "
            f"{result.pages_scraped} pages in {result.duration_seconds:.1f}s"
        )
        return result

    def _walk_paginated(self, base_url: str, result: ScrapeResult,
                        max_pages: Optional[int] = None) -> None:
        """
        Walk every page of a single category URL, appending each batch of
        listings to the shared ScrapeResult. Stops when the site stops
        offering a 'next' link or max_pages is reached.
        """
        page = 1
        page_cap = max_pages if max_pages is not None else self.settings.MAX_PAGES
        while page <= page_cap:
            url = build_page_url(base_url, page)
            logger.info(f"Page {page}: {url}")
            html = self._make_request(url)
            if html is None:
                result.errors.append(f"Failed to fetch page {page} of {base_url}")
                return

            listings = self._extract_listings_from_page(html)
            result.listings.extend(listings)
            result.total_listings_found += len(listings)
            result.pages_scraped += 1

            logger.info(f"Found {len(listings)} listings on page {page}")

            if not self._has_next_page(html, page):
                return

            page += 1

    def close(self):
        """Clean up resources"""
        self.session.close()


def scrape_kleinanzeigen(bundesland: str,
                         bundesland_url_param: str,
                         location_id: Optional[str] = None,
                         walk_sub_locations: bool = True) -> ScrapeResult:
    """
    Convenience function to scrape Kleinanzeigen for a Bundesland.

    Args:
        bundesland: Display name of the Bundesland (e.g. 'Bayern').
        bundesland_url_param: URL slug (e.g. 'bayern').
        location_id: Numeric locationId from bundesland_mapping.json.
        walk_sub_locations: If True (default), also walk every city-level
            search inside the state. Set to False for state-only scan.

    Returns:
        ScrapeResult object.
    """
    scraper = KleinanzeigenScraper()
    try:
        return scraper.scrape_bundesland(bundesland, bundesland_url_param,
                                        location_id,
                                        walk_sub_locations=walk_sub_locations)
    finally:
        scraper.close()