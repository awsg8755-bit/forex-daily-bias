"""
Pulls high/medium impact economic calendar events for the trading day
(Brisbane 7am-7am window) and maps them to the tracked pairs.

Source: ForexFactory's public calendar feed (no API key required).
"""

import json
import os
import time
import urllib.request
from datetime import datetime, timedelta, timezone

CALENDAR_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
CACHE_PATH = os.path.join(os.path.dirname(__file__), "data", "calendar_cache.json")
CACHE_TTL_SECONDS = 3600  # 1 hour
BRISBANE_TZ = timezone(timedelta(hours=10))
IMPACT_LEVELS = {"High", "Medium"}

PAIR_CURRENCIES = {
    "XAUUSD": ["USD"],
    "GBPJPY": ["GBP", "JPY"],
    "GBPUSD": ["GBP", "USD"],
    "EURGBP": ["EUR", "GBP"],
    "EURUSD": ["EUR", "USD"],
    "AUDJPY": ["AUD", "JPY"],
    "USDJPY": ["USD", "JPY"],
}


def _read_cache():
    try:
        with open(CACHE_PATH) as f:
            cache = json.load(f)
        if time.time() - cache["fetched_at"] < CACHE_TTL_SECONDS:
            return cache["events"]
    except (FileNotFoundError, KeyError, ValueError):
        pass
    return None


def _write_cache(events):
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, "w") as f:
        json.dump({"fetched_at": time.time(), "events": events}, f)


def fetch_calendar():
    cached = _read_cache()
    if cached is not None:
        return cached

    req = urllib.request.Request(CALENDAR_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        events = json.load(resp)
    _write_cache(events)
    return events


def trading_day_window(now=None):
    """Brisbane 7am-7am trading day window containing `now` (default: current time)."""
    now = now or datetime.now(BRISBANE_TZ)
    anchor = now.replace(hour=7, minute=0, second=0, microsecond=0)
    start = anchor if now >= anchor else anchor - timedelta(days=1)
    return start, start + timedelta(days=1)


def events_for_pair(events, pair, window):
    start, end = window
    currencies = PAIR_CURRENCIES.get(pair, [])
    matches = []
    for e in events:
        if e.get("country") not in currencies:
            continue
        if e.get("impact") not in IMPACT_LEVELS:
            continue
        try:
            event_time = datetime.fromisoformat(e["date"]).astimezone(BRISBANE_TZ)
        except (KeyError, ValueError, TypeError):
            continue
        if start <= event_time < end:
            matches.append({
                "title": e.get("title", "Event"),
                "country": e.get("country"),
                "impact": e.get("impact"),
                "time": event_time.strftime("%I:%M%p").lstrip("0"),
            })
    matches.sort(key=lambda m: m["time"])
    return matches


def load_events_by_pair(pairs, window=None):
    window = window or trading_day_window()
    try:
        events = fetch_calendar()
    except Exception:
        return {pair: [] for pair in pairs}
    return {pair: events_for_pair(events, pair, window) for pair in pairs}
