"""Simple in-memory hourly rate limit per API key (single-process)."""

from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import HTTPException

_windows: dict[str, deque[float]] = defaultdict(deque)


def check_rate_limit(key_id: str, *, limit_per_hour: int) -> None:
    now = time.time()
    window = _windows[key_id]
    cutoff = now - 3600
    while window and window[0] < cutoff:
        window.popleft()
    if len(window) >= limit_per_hour:
        raise HTTPException(status_code=429, detail="rate limit exceeded (try again later)")
    window.append(now)
