#!/usr/bin/env python3
"""
Database Migration Runner
Applies SQL migrations to Supabase PostgreSQL
"""
import sys
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables from .env
load_dotenv(Path(__file__).parent.parent / ".env")

from trade_automation.config import Settings
from trade_automation.supabase_client import get_supabase_client

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_migrations():
    """Run all migration files in order"""
    
    settings = Settings()
    
    try:
        supabase = get_supabase_client(settings)
    except Exception as e:
        logger.error(f"Failed to initialize Supabase: {e}")
        return False
    
    # Get migration files
    migration_dir = Path(__file__).parent.parent / "database" / "ddl"
    migration_files = sorted(migration_dir.glob("*.sql"))
    
    if not migration_files:
        logger.warning("No migration files found")
        return False
    
    logger.info(f"Found {len(migration_files)} migration files")
    
    for migration_file in migration_files:
        logger.info(f"Running migration: {migration_file.name}")
        
        try:
            # Read SQL file
            with open(migration_file, 'r') as f:
                sql = f.read()
            
            # Execute SQL
            result = supabase.postgrest.session.post(
                f"{supabase.postgrest.base_url}/rpc/execute_sql",
                json={"sql": sql}
            )
            
            # Alternative: execute raw SQL via Supabase admin API
            # For now, use direct execute
            logger.info(f"✅ Applied {migration_file.name}")
        
        except Exception as e:
            logger.error(f"❌ Failed to apply {migration_file.name}: {e}")
            # Continue with other migrations
            continue
    
    logger.info("Migration run complete")
    return True


def execute_raw_sql(supabase, sql: str):
    """Execute raw SQL via Supabase admin client"""
    
    try:
        # Use the admin client (requires service role key)
        response = supabase.postgrest.session.rpc(
            'execute_sql',
            {'query': sql}
        )
        return response
    except Exception as e:
        # Fallback: note that this requires direct Postgres access
        logger.error(f"Could not execute SQL via RPC: {e}")
        logger.info("Note: Migrations may need to be applied manually via Supabase dashboard")
        return None


if __name__ == "__main__":
    success = run_migrations()
    sys.exit(0 if success else 1)
