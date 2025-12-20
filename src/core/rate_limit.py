from slowapi import Limiter
from slowapi.util import get_remote_address

from core import settings


# ============================================================================
# Rate Limiter Setup
# ============================================================================
# Initialize rate limiter with Redis backend
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.redis_url_str,
    default_limits=[settings.rate_limit_default],  # Global rate limit
    enabled=settings.rate_limit_enabled,
)
