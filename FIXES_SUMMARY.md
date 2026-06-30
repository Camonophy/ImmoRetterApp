# Fixes Summary for ImmoRetter Project

> **Note**: This document describes the historical fixes applied to the project. The current implementation uses **5 curated subcategories** (c196, c198, c203, c207, c208) as defined in `config/settings.py`. See [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) for the current state.

## Round 2 \u2014 Surfacing Old Listings in the Bundesland

### Problem Statement
After round 1 the scraper worked correctly per spec but only ever found listings from
the **state-level** search. A user-provided example \u2014

> https://www.kleinanzeigen.de/s-anzeige/schoenes-chalet-in-huenxe-baujahr-2014-winterfest-zu-verkaufen/3110176588-208-1389

(H\u00fcnxe, NRW, activation date `13.06.2025`, age 380 days, a private-seller listing)
\u2014 was **not** returned. Live HTTP probing against modern Kleinanzeigen.de revealed
three root causes.

### Root Causes

1. **Wrong subcategory codes.** The previous config walked slug-based URLs
   (`/mietwohnung/`, `/wohnung/`, etc.) which actually only do a **free-text**
   search inside c195, not a true category filter. The user's listing is in
   `c208` ("H\u00e4user zum Kauf"), which was missing from the slug set.
2. **Default search shows commercial listings.** Without `posterType=PRIVATE`
   Kleinanzeigen surfaces 44,774 NRW H\u00e4user-zum-Kauf results, almost all
   from real-estate agencies. The user's listing (a private seller) is
   filtered out.
3. **State-level pagination is rate-limited.** With `posterType=PRIVATE`
   the same NRW search returns 3,019 results \u2014 but the site only allows
   ~3 pages of `?o=N` pagination before re-serving the same cards. The
   user's listing is too deep in the result set to surface on the state
   page. **Sub-location searches** (one city at a time) have \u2264100 results
   each and paginate completely.

### Fixes Applied

#### 1. Switch from slug-based to category-code URLs
`REAL_ESTATE_SUBCATEGORIES` now uses the bare numeric codes verified against
the live site:

| Code | Category |
|------|----------|
| c195 | Immobilien (umbrella) |
| c196 | Eigentumswohnung kaufen |
| c197 | Garage & Lagerraum |
| c198 | Weitere Immobilien |
| c199 | Auf Zeit & WG |
| c203 | Mietwohnung |
| c205 | H\u00e4user zur Miete |
| c207 | Grundst\u00fccke & G\u00e4rten |
| c208 | H\u00e4user zum Kauf \u2190 contains the user's example |

> **Current state**: The implementation was later refined to use **5 curated categories** (c196, c198, c203, c207, c208) that are most useful for surfacing stale private-seller listings.

#### 2. Add `posterType=PRIVATE&sortingField=SORTING_DATE` to every search
Added as `Settings.DEFAULT_QUERY_PARAMS` and appended to every search URL.
- `posterType=PRIVATE` filters out commercial listings.
- `sortingField=SORTING_DATE` orders newest-first; combined with
  per-page walking, surfaces old listings as soon as we paginate deep
  enough.

#### 3. Add sub-location walker (Phase 2)
After the state-level phase, the scraper:
1. Fetches the sidebar of the state search page (via
   `utils.fetch_sub_locations`) to discover every city/PLZ area inside
   the Bundesland (NRW has ~407; capped at `SUB_LOC_BREADTH_LIMIT=100`).
2. For each sub-location, walks every configured category (\u22643 pages each).
3. De-duplicates by listing URL across phases.

The user's example listing (in Rees, locationId 1387) is found this way.

#### 4. Extract activation date directly from search cards
Modern Kleinanzeigen puts the activation date in `.aditem-main--top--right`
on every search-result card. Previously the scraper only fetched this from
the detail page (which is slower and not always available for sub-location
search cards). The new parser handles both formats:

- **Sub-location cards**: absolute date `"13.06.2025"`.
- **State-level cards**: relative date `"Heute, 19:18"`.

This also makes the date-fetching phase skippable for most listings
(sub-location cards already have the date), massively reducing runtime.

#### 5. Clean up the location field
Sub-location cards append a distance marker like `(6 km)` and use `\n`
whitespace inside the location text. The new parser strips these so the
Excel column reads cleanly.

### Verified End-to-End

Live test against NRW (state + 1 sub-location = Rees, locationId 1387):

| Stat | Value |
|---|---|
| Listings scraped (raw) | 473 |
| Listings after de-dup | 335 |
| Old listings (>90 days) | **20** |
| User's example listing | **\u2705 found** |
| Export file | `data/output/Nordrhein-Westfalen_real_estate_old_listings_*.xlsx` |

User's example row from the Excel:
| Field | Value |
|---|---|
| Title | Sch\u00f6nes Chalet in H\u00fcnxe, Baujahr 2014, winterfest, zu verkaufen |
| URL | https://www.kleinanzeigen.de/s-anzeige/schoenes-chalet-in-huenxe-baujahr-2014-winterfest-zu-verkaufen/3110176588-208-1389 |
| Price | 65.000 \u20ac |
| Location | 46459 Rees |
| Date Posted | 13.06.2025 |
| Age (Days) | 380 |
| Older than 3 months | Yes |

A wider run is currently walking the first 100 sub-locations of NRW.
Expected output: significantly more old listings in the Excel file.

---

## Round 1 \u2014 Initial Correctness

(Summary preserved below for context.)

### Original bugs found (round 1)

1. **Region filter ignored.** `data/bundesland_mapping.json` had no
   `location_id`; the URL `/s-immobilien/<bundesland>/<category>` returned
   nationwide results regardless of the Bundesland slug in the path.
2. **Subcategories mis-mapped.** The hard-coded `c198`-`c205` codes didn't
   match modern Kleinanzeigen \u2014 four of eight hit a generic landing page
   (0 listings), and the other four returned listings from the wrong
   categories than the comments claimed.
3. **Card selectors broken.** The `.price` and `.location` selectors
   returned `None` for every card on the modern DOM. Title, URL, price,
   location were mostly missing.
4. **Date extraction fragile.** `fetch_listing_date()` grabbed whichever
   date appeared first in the page, including unrelated dates (e.g. a
   user's "Aktiv seit" account-creation date in the seller profile).
5. **Counter bug.** `result.pages_scraped = page` overwrote instead of
   accumulating, so the field reported the page number of the LAST
   category visited rather than the total.
6. **Silent exporter fallback.** When no old listings were found the
   exporter wrote a file called `_old_listings_` containing recent
   listings \u2014 misleading.
7. **Sheet-name truncation.** Long Bundesland names like
   `Nordrhein-Westfalen Old Listings` exceed Excel's 31-char limit.
8. **MAX_LISTINGS_FOR_DATES debug cap.** Hard-coded at 500, so most
   fetched listings never got a date checked.
9. **Test runner lying.** `test_url_generation()` always returned `True`,
   hiding failing assertions.

### Round-1 fixes

See the [git history](https://...) for the diffs. Summary:

- Added `location_id` for every Bundesland in
  `data/bundesland_mapping.json`.
- New `IMMOBILIEN_CATEGORY` and `REAL_ESTATE_SUBCATEGORIES` (slug-based)
  in `config/settings.py`.
- Modern card selectors in `scraper/kleinanzeigen.py`
  (`h2.text-module-begin a`, `.aditem-main--middle--price-shipping--price`,
  `.aditem-main--top--left`).
- Detail-page date extraction scoped to `#viewad-extra-info`.
- `pages_scraped += 1` accumulator.
- Exporter split into `export_old_listings()` / `export_all_listings()`,
  `_safe_sheet_name()` truncates to 31 chars, no silent fallback.
- `MAX_LISTINGS_FOR_DATES` defaults to `None`.
- `test_basic.py` rewritten so it actually reports failures.
