"""Bounded, rate-limited football-data.org v4 client. Never logs credentials."""

import logging
import os
import time
from threading import Lock

import httpx

logger = logging.getLogger(__name__)


class ProviderError(RuntimeError):
    pass


class FootballData:
    def __init__(self, token=None, transport=None, interval=6.1, sleep=time.sleep):
        token = token or os.getenv("FOOTBALL_DATA_TOKEN")
        if not token:
            raise ProviderError("FOOTBALL_DATA_TOKEN is required for live mode")
        self.client = httpx.Client(
            base_url="https://api.football-data.org/v4/",
            headers={"X-Auth-Token": token},
            timeout=20,
            transport=transport,
        )
        self.interval, self.sleep = interval, sleep
        self.last = 0.0
        self.lock = Lock()

    def close(self):
        self.client.close()

    def get(self, endpoint: str) -> dict:
        with self.lock:
            for attempt in range(4):
                self.sleep(max(0, self.interval - (time.monotonic() - self.last)))
                self.last = time.monotonic()
                try:
                    response = self.client.get(endpoint)
                except httpx.RequestError:
                    if attempt == 3:
                        raise ProviderError("Provider network failure after 4 attempts") from None
                    self.sleep(2**attempt)
                    continue
                if response.status_code in (401, 403):
                    raise ProviderError(
                        "Endpoint unavailable: credentials or subscription do not permit access"
                    )
                if response.status_code == 429 or response.status_code >= 500:
                    logger.warning("Provider retry: HTTP %s", response.status_code)
                    try:
                        delay = float(response.headers.get("Retry-After", 2**attempt))
                    except ValueError:
                        delay = 2**attempt
                    self.sleep(min(60, max(0, delay)))
                    continue
                if response.is_error:
                    raise ProviderError(f"Provider HTTP {response.status_code}")
                try:
                    payload = response.json()
                    if not isinstance(payload, dict):
                        raise ValueError()
                    return payload
                except ValueError:
                    raise ProviderError("Provider returned invalid JSON") from None
            raise ProviderError("Provider retry limit exceeded")
