"""
Excel export functionality for Kleinanzeigen Scraper
"""

import os
from datetime import datetime
from typing import Optional

import pandas as pd

from .models import ScrapeResult
from config.settings import Settings


class ExcelExporter:
    """Export scrape results to Excel"""
    
    def __init__(self, settings: Settings = None):
        self.settings = settings or Settings()
    
    def export_result(self, result: ScrapeResult) -> Optional[str]:
        """
        Export scrape result to Excel file
        
        Args:
            result: ScrapeResult to export
        
        Returns:
            Path to created Excel file or None if failed
        """
        if not result.listings:
            return None
        
        # Get old listings only
        old_listings = result.get_old_listings()
        
        if not old_listings:
            return None
        
        # Create DataFrame from listings
        data = [listing.to_dict() for listing in old_listings]
        df = pd.DataFrame(data)
        
        # Reorder columns for better readability
        column_order = [
            "Title",
            "URL",
            "Price", 
            "Location",
            "Date Posted",
            "Age (Days)",
            "Older than 3 months"
        ]
        df = df[column_order]
        
        # Generate filename
        timestamp = datetime.now().strftime(self.settings.EXCEL_DATE_FORMAT)
        filename = self.settings.EXCEL_FILENAME_TEMPLATE.format(
            bundesland=result.bundesland.replace(" ", "_"),
            timestamp=timestamp
        )
        
        # Ensure output directory exists
        os.makedirs(self.settings.OUTPUT_DIR, exist_ok=True)
        
        # Full file path
        filepath = self.settings.OUTPUT_DIR / filename
        
        # Export to Excel
        try:
            # Use openpyxl engine for better Excel compatibility
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                df.to_excel(
                    writer,
                    sheet_name=f"{result.bundesland} Old Listings",
                    index=False
                )
                
                # Add a summary sheet
                summary_df = pd.DataFrame([result.to_summary_dict()])
                summary_df.to_excel(
                    writer,
                    sheet_name="Summary",
                    index=False
                )
            
            return str(filepath)
            
        except Exception as e:
            print(f"Error exporting to Excel: {e}")
            return None
    
    def export_all_listings(self, result: ScrapeResult) -> Optional[str]:
        """
        Export ALL listings (not just old ones) to Excel
        
        Args:
            result: ScrapeResult to export
        
        Returns:
            Path to created Excel file or None if failed
        """
        if not result.listings:
            return None
        
        # Create DataFrame from all listings
        data = [listing.to_dict() for listing in result.listings]
        df = pd.DataFrame(data)
        
        # Reorder columns
        column_order = [
            "Title",
            "URL",
            "Price",
            "Location", 
            "Date Posted",
            "Age (Days)",
            "Older than 3 months"
        ]
        df = df[column_order]
        
        # Generate filename
        timestamp = datetime.now().strftime(self.settings.EXCEL_DATE_FORMAT)
        filename = f"{result.bundesland.replace(' ', '_')}_all_listings_{timestamp}.xlsx"
        
        # Ensure output directory exists
        os.makedirs(self.settings.OUTPUT_DIR, exist_ok=True)
        
        # Full file path
        filepath = self.settings.OUTPUT_DIR / filename
        
        # Export to Excel
        try:
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                df.to_excel(
                    writer,
                    sheet_name=f"{result.bundesland} All Listings",
                    index=False
                )
                
                # Add a summary sheet
                summary_df = pd.DataFrame([result.to_summary_dict()])
                summary_df.to_excel(
                    writer,
                    sheet_name="Summary",
                    index=False
                )
            
            return str(filepath)
            
        except Exception as e:
            print(f"Error exporting all listings to Excel: {e}")
            return None


def export_to_excel(result: ScrapeResult) -> Optional[str]:
    """
    Convenience function to export scrape result to Excel
    
    Args:
        result: ScrapeResult to export
    
    Returns:
        Path to created Excel file or None if failed
    """
    exporter = ExcelExporter()
    filepath = exporter.export_result(result)
    
    # If no old listings were found, export all listings instead
    if filepath is None and result.listings:
        filepath = exporter.export_all_listings(result)
    
    return filepath
