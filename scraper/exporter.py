"""
Excel export functionality for Kleinanzeigen Scraper
"""

import os
from datetime import datetime
from typing import Optional, List

import pandas as pd
import openpyxl.utils.exceptions

from .models import ScrapeResult
from config.settings import Settings


# Excel sheet names are limited to 31 chars.
_MAX_SHEET_LEN = 31


def _safe_sheet_name(name: str) -> str:
    """Truncate and sanitize a string to be a valid Excel sheet name."""
    # Excel disallows [ ] : * ? / \ and a few others in sheet names.
    safe = "".join("_" if c in "[]:*?/\\" else c for c in name)
    if len(safe) > _MAX_SHEET_LEN:
        safe = safe[:_MAX_SHEET_LEN]
    return safe


class ExcelExporter:
    """Export scrape results to Excel."""

    def __init__(self, settings: Settings = None):
        self.settings = settings or Settings()

    # ------------------------------------------------------------------
    # Old listings only
    # ------------------------------------------------------------------
    def export_old_listings(self, result: ScrapeResult) -> Optional[str]:
        """
        Export only listings older than MIN_AGE_DAYS.

        Returns the file path, or None if there were no old listings
        (caller is responsible for deciding whether to fall back to
        exporting everything — we don't do that silently here).
        """
        if not result.listings:
            return None

        old_listings = result.get_old_listings()
        if not old_listings:
            return None

        return self._write_excel(
            listings=old_listings,
            result=result,
            kind="old",
            sheet_label="Old Listings",
            filename_template=self.settings.EXCEL_FILENAME_TEMPLATE,
        )

    # ------------------------------------------------------------------
    # All listings
    # ------------------------------------------------------------------
    def export_all_listings(self, result: ScrapeResult) -> Optional[str]:
        """Export every listing (regardless of age)."""
        if not result.listings:
            return None
        return self._write_excel(
            listings=result.listings,
            result=result,
            kind="all",
            sheet_label="All Listings",
            filename_template="{bundesland}_real_estate_listings_{timestamp}.xlsx",
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    def _write_excel(self,
                     listings: List,
                     result: ScrapeResult,
                     kind: str,
                     sheet_label: str,
                     filename_template: str) -> Optional[str]:
        column_order = [
            "Title",
            "URL",
            "Price",
            "Location",
            "Date Posted",
            "Age (Days)",
            "Older than 3 months",
        ]
        df = pd.DataFrame([l.to_dict() for l in listings])
        df = df[column_order]

        timestamp = datetime.now().strftime(self.settings.EXCEL_DATE_FORMAT)
        filename = filename_template.format(
            bundesland=result.bundesland.replace(" ", "_"),
            timestamp=timestamp,
        )
        os.makedirs(self.settings.OUTPUT_DIR, exist_ok=True)
        filepath = self.settings.OUTPUT_DIR / filename

        sheet_name = _safe_sheet_name(f"{result.bundesland} {sheet_label}")

        try:
            with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                summary_df = pd.DataFrame([result.to_summary_dict()])
                summary_df.to_excel(writer, sheet_name="Summary", index=False)
            return str(filepath)
        except (OSError, ValueError,
                openpyxl.utils.exceptions.IllegalCharacterError) as e:
            print(f"Error exporting to Excel: {e}")
            return None


# ----------------------------------------------------------------------
# Module-level helper
# ----------------------------------------------------------------------
def export_to_excel(result: ScrapeResult, allow_all_fallback: bool = False) -> Optional[str]:
    """
    Convenience export function.

    By default this exports ONLY the listings older than MIN_AGE_DAYS,
    and returns None if none were found. If ``allow_all_fallback`` is
    True (or the user passes --all on the CLI), it will instead export
    every listing it found.

    The previous behaviour silently renamed an "all listings" file to
    "..._old_listings_..." which was misleading. This version makes the
    decision explicit at the call site.
    """
    exporter = ExcelExporter()
    if allow_all_fallback:
        return exporter.export_all_listings(result)
    return exporter.export_old_listings(result)