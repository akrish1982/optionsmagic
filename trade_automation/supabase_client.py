from supabase import create_client
from trade_automation.config import Settings


def get_supabase_client(settings: Settings):
    key = settings.supabase_auth_key()
    if not settings.supabase_url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY or SUPABASE_SERVICE_ROLE_KEY must be set")
    return create_client(settings.supabase_url, key)
