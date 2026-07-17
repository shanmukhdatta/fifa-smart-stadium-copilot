from slowapi import Limiter
from slowapi.util import get_remote_address

# Shared Limiter instance registered across all routers (auth, chat) to enforce rate limits
limiter = Limiter(key_func=get_remote_address)
