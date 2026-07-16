"""HTTP helper with NSE-safe headers, on-disk cache, and retries."""
from __future__ import annotations

import hashlib
from pathlib import Path

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import settings

# NSE blocks default UA and requires a warm-up cookie fetch on some endpoints.
NSE_HEADERS = {
    "User-Agent": settings.ingest_user_agent,
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
}


def _cache_path(url: str, subdir: str) -> Path:
    key = hashlib.sha1(url.encode()).hexdigest()[:16]
    out_dir = settings.ingest_cache_dir / subdir
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / f"{key}.bin"


@retry(
    reraise=True,
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, min=1, max=30),
    retry=retry_if_exception_type((httpx.HTTPError,)),
)
def fetch(
    url: str,
    *,
    subdir: str = "misc",
    use_cache: bool = True,
    headers: dict[str, str] | None = None,
    warmup_url: str | None = None,
    timeout: float = 30.0,
) -> bytes:
    """Fetch a URL with retries; cache raw response to disk by URL hash.

    warmup_url: optional URL hit first (with a shared client) to seed cookies —
    NSE requires this for many JSON endpoints.
    """
    path = _cache_path(url, subdir)
    if use_cache and path.exists() and path.stat().st_size > 0:
        return path.read_bytes()

    merged = {**NSE_HEADERS, **(headers or {})}
    with httpx.Client(headers=merged, timeout=timeout, follow_redirects=True) as client:
        if warmup_url:
            client.get(warmup_url)
        r = client.get(url)
        r.raise_for_status()
        path.write_bytes(r.content)
        return r.content
