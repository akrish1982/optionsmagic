"""
Data Retention Cleanup Script

Deletes data older than 30 days from all tables to keep database lean.
Runs weekly via cron to maintain 30-day rolling window.

Usage:
    poetry run python data_collection/cleanup_old_data.py [--dry-run]

Author: Max 👨‍💻
Date: 2026-02-10
"""

import os
import sys
import logging
from datetime import date, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/cleanup.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Supabase configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

# Retention period
RETENTION_DAYS = 30

from supabase import create_client


def get_supabase_client():
    """Get Supabase client."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def cleanup_table(supabase, table_name, date_column, dry_run=False):
    """
    Delete records older than RETENTION_DAYS from a table.
    
    Args:
        supabase: Supabase client
        table_name: Name of table to clean
        date_column: Name of date column to filter on
        dry_run: If True, only count records without deleting
    
    Returns:
        Number of records deleted (or would be deleted if dry_run)
    """
    try:
        # Calculate cutoff date
        cutoff_date = date.today() - timedelta(days=RETENTION_DAYS)
        cutoff_str = cutoff_date.isoformat()
        
        logger.info(f"Processing table: {table_name}")
        logger.info(f"  Date column: {date_column}")
        logger.info(f"  Cutoff date: {cutoff_str} ({RETENTION_DAYS} days ago)")
        
        # Count records to be deleted
        count_response = supabase.table(table_name).select(
            'count', count='exact'
        ).lt(date_column, cutoff_str).execute()
        
        count = count_response.count if hasattr(count_response, 'count') else 0
        
        if count == 0:
            logger.info(f"  ✅ No old records found in {table_name}")
            return 0
        
        if dry_run:
            logger.info(f"  🔍 DRY RUN: Would delete {count} records from {table_name}")
            return count
        
        # Delete old records
        delete_response = supabase.table(table_name).delete().lt(
            date_column, cutoff_str
        ).execute()
        
        logger.info(f"  ✅ Deleted {count} old records from {table_name}")
        return count
        
    except Exception as e:
        logger.error(f"  ❌ Error cleaning {table_name}: {e}")
        return 0


def main():
    """Main cleanup execution."""
    # Check for dry-run flag
    dry_run = '--dry-run' in sys.argv
    
    if dry_run:
        logger.info("🔍 DRY RUN MODE - No data will be deleted")
    else:
        logger.info("🧹 CLEANUP MODE - Deleting old data")
    
    logger.info(f"📅 Retention period: {RETENTION_DAYS} days")
    logger.info("")
    
    try:
        # Get Supabase client
        supabase = get_supabase_client()
        
        total_deleted = 0
        
        # Clean each table
        tables_to_clean = [
            ('stock_quotes', 'quote_date'),
            ('options_quotes', 'date'),
            ('options_opportunities', 'last_updated'),
        ]
        
        for table_name, date_column in tables_to_clean:
            deleted = cleanup_table(supabase, table_name, date_column, dry_run)
            total_deleted += deleted
            logger.info("")
        
        # Summary
        if dry_run:
            logger.info(f"🔍 DRY RUN SUMMARY: Would delete {total_deleted} total records")
        else:
            logger.info(f"✅ CLEANUP COMPLETE: Deleted {total_deleted} total records")
        
        logger.info(f"📊 Database now contains only data from last {RETENTION_DAYS} days")
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Cleanup failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
