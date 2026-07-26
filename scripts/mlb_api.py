"""Thin wrapper around the public MLB Stats API (statsapi.mlb.com).

Standard library only - no pip installs required.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone

BASE = "https://statsapi.mlb.com/api/v1"
USER_AGENT = "mlb-daily-results/1.0 (+https://github.com/)"

# MLB "official date" rolls over on US Eastern time.
EASTERN = timezone(timedelta(hours=-4))  # EDT; close enough for date bucketing

SCHEDULE_HYDRATE = ",".join(
    [
        "linescore",
        "decisions",
        "team",
        "venue",
        "homeRuns",
        "seriesStatus",
        "gameInfo",
        "weather",
        "flags",
        "probablePitcher",
    ]
)


def _get(path: str, params: dict | None = None, retries: int = 4) -> dict:
    url = f"{BASE}/{path.lstrip('/')}"
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=45) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as err:
            last_err = err
            time.sleep(2 ** attempt)
    raise RuntimeError(f"MLB API request failed after {retries} tries: {url}") from last_err


def eastern_today() -> date:
    return datetime.now(EASTERN).date()


def schedule(day: date) -> dict:
    return _get(
        "schedule",
        {"sportId": 1, "date": day.isoformat(), "hydrate": SCHEDULE_HYDRATE},
    )


def standings(season: int) -> dict:
    return _get(
        "standings",
        {"leagueId": "103,104", "season": season, "standingsTypes": "regularSeason"},
    )


def divisions() -> dict:
    return _get("divisions", {"sportId": 1})
