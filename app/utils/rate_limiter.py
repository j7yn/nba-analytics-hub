import time
from functools import wraps
from typing import Dict, List
from fastapi import HTTPException
from ..core.config import settings
from ..core.exceptions import RateLimitExceededError

class RateLimiter:
    def __init__(self):
        self.call_history: Dict[str, List[float]] = {}
    
    def is_allowed(self, identifier: str, max_calls: int = None, period: int = None) -> bool:
        """Check if request is allowed based on rate limit"""
        max_calls = max_calls or settings.rate_limit_calls
        period = period or settings.rate_limit_period
        
        current_time = time.time()
        
        # clean old entries
        if identifier in self.call_history:
            self.call_history[identifier] = [
                call_time for call_time in self.call_history[identifier]
                if current_time - call_time < period
            ]
        else:
            self.call_history[identifier] = []
        
        # check if under limit
        if len(self.call_history[identifier]) >= max_calls:
            return False
        
        # qdd current call
        self.call_history[identifier].append(current_time)
        return True

rate_limiter = RateLimiter()

def rate_limit(calls_per_minute: int = None, identifier_func=None):
    """Rate limiting decorator"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # extract identifier (could be IP, user ID, etc)
            identifier = "default"
            if identifier_func:
                identifier = identifier_func(*args, **kwargs)
            
            if not rate_limiter.is_allowed(identifier, calls_per_minute):
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded. Max {calls_per_minute or settings.rate_limit_calls} calls per minute."
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator