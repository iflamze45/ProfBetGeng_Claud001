"""
Supabase client factory — M3 Step 1
Returns a cached production client when credentials are present.
Falls back gracefully to None so Mock services remain usable without env vars.
"""
from functools import lru_cache
from typing import Optional


@lru_cache()
def get_supabase_client():
    """
    Return a cached Supabase client.
    Returns None if SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY are not set —
    callers fall back to Mock services in that case.
    """
    from ..config import get_settings
    settings = get_settings()

    if not settings.supabase_url or not settings.supabase_service_role_key:
        return None

    from supabase import create_client
    return create_client(settings.supabase_url, settings.supabase_service_role_key)
