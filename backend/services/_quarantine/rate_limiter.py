"""
RateLimiter — Strategic Request Gating
Simple in-memory rate limiter for PBG API nodes.
"""
import time
from collections import deque
from fastapi import HTTPException

class RateLimiter:
    """
    HUD-aligned rate limiter.
    Limits requests per unique key over a sliding window.
    """
    def __init__(self, requests: int = 60, window: int = 60):
        self.requests = requests
        self.window = window
        self._history = {}

    def check(self, key: str):
        """
        Gates the request. 
        Raises 429 if threshold exceeded.
        """
        now = time.time()
        if key not in self._history:
            self._history[key] = deque()
        
        # Prune old requests
        history = self._history[key]
        while history and history[0] < now - self.window:
            history.popleft()
            
        if len(history) >= self.requests:
            raise HTTPException(
                status_code=429, 
                detail=f"THRESHOLD_EXCEEDED: Max {self.requests} requests per {self.window}s"
            )
            
        history.append(now)

# Singleton for project-wide use
limiter = RateLimiter(requests=60, window=60)
