"""Collect MLB game results for one or more dates and store them as JSON + CSV.

Usage:
    python scripts/collect.py                 # yesterday + today (US/Eastern)
    python scripts/collect.py --date 2026-07-04
    python scripts/collect.py --start 2026-03-26 --end 2026-04-05
    python scripts/collect.py --backfill 10   # last 10 days
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import mlb_api

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
GAMES_DIR = DATA / "games"
CSV_DIR = DATA / "csv"

GAME_TYPES = {
    "R": "Regular Season",
    "F": "Wild Card",
    "D": "Division Series",
    "L": "League Championship Series",
    "W": "World Series",
    "S": "Spring Training",
    "E": "Exhibition",
    "A": "All-Star Game",
    "P": "Playoffs",
}

CSV_FIELDS = [
    "date",
    "game_pk",
    "game_type",
    "status",
    "away_team",
    "away_abbr",
    "away_score",
    "home_team",
    "home_abbr",
    "home_score",
    "winner",
    "innings",
    "away_hits",
    "home_hits",
    "away_errors",
    "home_errors",
    "winning_pitcher",
    "losing_pitcher",
    "save_pitcher",
    "venue",
    "attendance",
    "duration_minutes",
    "day_night",
    "first_pitch_utc",
]


def _side(game: dict, which: str) -> dict:
    return game.get("teams", {}).get(which, {}) or {}


def _linescore_totals(ls: dict, which: str) -> dict:
    return (ls.get("teams", {}) or {}).get(which, {}) or {}


def normalize_game(game: dict) -> dict:
    ls = game.get("linescore") or {}
    away, home = _side(game, "away"), _side(game, "home")
    away_team, home_team = away.get("team", {}) or {}, home.get("team", {}) or {}
    decisions = game.get("decisions") or {}
    info = game.get("gameInfo") or {}
    status = game.get("status", {}) or {}
    state = status.get("abstractGameState", "")
    detailed = status.get("detailedState", "")

    innings = []
    for inn in ls.get("innings", []) or []:
        innings.append(
            {
                "num": inn.get("num"),
                "away": (inn.get("away", {}) or {}).get("runs"),
                "home": (inn.get("home", {}) or {}).get("runs"),
            }
        )

    home_runs = []
    for hr in game.get("homeRuns", []) or []:
        home_runs.append(
            {
                "batter": (hr.get("matchup", {}) or {}).get("batter", {}).get("fullName"),
                "pitcher": (hr.get("matchup", {}) or {}).get("pitcher", {}).get("fullName"),
                "inning": (hr.get("about", {}) or {}).get("inning"),
                "half": (hr.get("about", {}) or {}).get("halfInning"),
                "rbi": (hr.get("result", {}) or {}).get("rbi"),
            }
        )

    is_final = state == "Final"
    away_score, home_score = away.get("score"), home.get("score")
    winner = None
    if is_final and away_score is not None and home_score is not None:
        if away_score > home_score:
            winner = away_team.get("abbreviation")
        elif home_score > away_score:
            winner = home_team.get("abbreviation")
        else:
            winner = "TIE"

    def person(key: str) -> str | None:
        return (decisions.get(key) or {}).get("fullName")

    def probable(side: dict) -> str | None:
        return (side.get("probablePitcher") or {}).get("fullName")

    return {
        "game_pk": game.get("gamePk"),
        "date": game.get("officialDate"),
        "game_type": game.get("gameType"),
        "game_type_label": GAME_TYPES.get(game.get("gameType", ""), game.get("gameType")),
        "series_description": game.get("seriesDescription"),
        "series_status": (game.get("seriesStatus") or {}).get("shortDescription"),
        "double_header": game.get("doubleHeader"),
        "game_number": game.get("gameNumber"),
        "state": state,
        "status": detailed,
        "is_final": is_final,
        "start_time_utc": game.get("gameDate"),
        "day_night": game.get("dayNight"),
        "scheduled_innings": game.get("scheduledInnings"),
        "innings_played": ls.get("currentInning") if is_final else ls.get("currentInning"),
        "venue": (game.get("venue") or {}).get("name"),
        "attendance": info.get("attendance"),
        "duration_minutes": info.get("gameDurationMinutes"),
        "weather": game.get("weather") or {},
        "flags": {k: v for k, v in (game.get("flags") or {}).items() if v},
        "winner_abbr": winner,
        "teams": {
            "away": {
                "id": away_team.get("id"),
                "name": away_team.get("name"),
                "abbr": away_team.get("abbreviation"),
                "short": away_team.get("shortName"),
                "club": away_team.get("clubName"),
                "division": (away_team.get("division") or {}).get("name"),
                "league": (away_team.get("league") or {}).get("name"),
                "score": away_score,
                "hits": _linescore_totals(ls, "away").get("hits"),
                "errors": _linescore_totals(ls, "away").get("errors"),
                "left_on_base": _linescore_totals(ls, "away").get("leftOnBase"),
                "record": away.get("leagueRecord") or {},
                "is_winner": away.get("isWinner"),
                "probable_pitcher": probable(away),
            },
            "home": {
                "id": home_team.get("id"),
                "name": home_team.get("name"),
                "abbr": home_team.get("abbreviation"),
                "short": home_team.get("shortName"),
                "club": home_team.get("clubName"),
                "division": (home_team.get("division") or {}).get("name"),
                "league": (home_team.get("league") or {}).get("name"),
                "score": home_score,
                "hits": _linescore_totals(ls, "home").get("hits"),
                "errors": _linescore_totals(ls, "home").get("errors"),
                "left_on_base": _linescore_totals(ls, "home").get("leftOnBase"),
                "record": home.get("leagueRecord") or {},
                "is_winner": home.get("isWinner"),
                "probable_pitcher": probable(home),
            },
        },
        "innings": innings,
        "decisions": {
            "winner": person("winner"),
            "loser": person("loser"),
            "save": person("save"),
        },
        "home_runs": home_runs,
        "mlb_link": f"https://www.mlb.com/gameday/{game.get('gamePk')}",
    }


def collect_day(day: date) -> dict:
    payload = mlb_api.schedule(day)
    games: list[dict] = []
    for date_block in payload.get("dates", []) or []:
        for game in date_block.get("games", []) or []:
            games.append(normalize_game(game))

    games.sort(key=lambda g: (g.get("start_time_utc") or "", g.get("game_pk") or 0))
    finals = [g for g in games if g["is_final"]]

    return {
        "date": day.isoformat(),
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_games": len(games),
        "final_games": len(finals),
        "total_runs": sum(
            (g["teams"]["away"]["score"] or 0) + (g["teams"]["home"]["score"] or 0)
            for g in finals
        ),
        "games": games,
        "source": "MLB Stats API (statsapi.mlb.com)",
    }


def write_day(day_data: dict) -> Path:
    day = day_data["date"]
    year = day[:4]
    out_dir = GAMES_DIR / year
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{day}.json"
    path.write_text(json.dumps(day_data, indent=2) + "\n", encoding="utf-8")
    return path


def csv_row(game: dict) -> dict:
    away, home = game["teams"]["away"], game["teams"]["home"]
    return {
        "date": game["date"],
        "game_pk": game["game_pk"],
        "game_type": game["game_type"],
        "status": game["status"],
        "away_team": away["name"],
        "away_abbr": away["abbr"],
        "away_score": away["score"],
        "home_team": home["name"],
        "home_abbr": home["abbr"],
        "home_score": home["score"],
        "winner": game["winner_abbr"],
        "innings": game["innings_played"],
        "away_hits": away["hits"],
        "home_hits": home["hits"],
        "away_errors": away["errors"],
        "home_errors": home["errors"],
        "winning_pitcher": game["decisions"]["winner"],
        "losing_pitcher": game["decisions"]["loser"],
        "save_pitcher": game["decisions"]["save"],
        "venue": game["venue"],
        "attendance": game["attendance"],
        "duration_minutes": game["duration_minutes"],
        "day_night": game["day_night"],
        "first_pitch_utc": game["start_time_utc"],
    }


def rebuild_season_csv(year: str) -> Path | None:
    day_files = sorted((GAMES_DIR / year).glob("*.json"))
    if not day_files:
        return None
    CSV_DIR.mkdir(parents=True, exist_ok=True)
    path = CSV_DIR / f"{year}.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for day_file in day_files:
            day_data = json.loads(day_file.read_text(encoding="utf-8"))
            for game in day_data["games"]:
                if game["is_final"]:
                    writer.writerow(csv_row(game))
    return path


def save_standings(season: int) -> Path:
    raw = mlb_api.standings(season)
    div_names = {
        200: "AL West", 201: "AL East", 202: "AL Central",
        203: "NL West", 204: "NL East", 205: "NL Central",
    }
    out = {
        "season": season,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "divisions": [],
    }
    for record in raw.get("records", []) or []:
        div_id = (record.get("division") or {}).get("id")
        teams = []
        for tr in record.get("teamRecords", []) or []:
            lr = tr.get("leagueRecord", {}) or {}
            teams.append(
                {
                    "rank": tr.get("divisionRank"),
                    "team": (tr.get("team") or {}).get("name"),
                    "team_id": (tr.get("team") or {}).get("id"),
                    "wins": lr.get("wins"),
                    "losses": lr.get("losses"),
                    "pct": lr.get("pct"),
                    "games_back": tr.get("divisionGamesBack"),
                    "wc_games_back": tr.get("wildCardGamesBack"),
                    "streak": (tr.get("streak") or {}).get("streakCode"),
                    "runs_scored": tr.get("runsScored"),
                    "runs_allowed": tr.get("runsAllowed"),
                    "run_differential": tr.get("runDifferential"),
                }
            )
        teams.sort(key=lambda t: int(t["rank"]) if str(t["rank"]).isdigit() else 99)
        out["divisions"].append(
            {"id": div_id, "name": div_names.get(div_id, str(div_id)), "teams": teams}
        )
    out["divisions"].sort(key=lambda d: d["name"])
    DATA.mkdir(parents=True, exist_ok=True)
    path = DATA / "standings.json"
    path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    return path


def daterange(start: date, end: date):
    cur = start
    while cur <= end:
        yield cur
        cur += timedelta(days=1)


def main() -> None:
    ap = argparse.ArgumentParser(description="Collect MLB results")
    ap.add_argument("--date", help="single date YYYY-MM-DD")
    ap.add_argument("--start", help="start date YYYY-MM-DD")
    ap.add_argument("--end", help="end date YYYY-MM-DD")
    ap.add_argument("--backfill", type=int, help="collect the last N days")
    ap.add_argument("--skip-standings", action="store_true")
    args = ap.parse_args()

    today = mlb_api.eastern_today()

    if args.date:
        days = [date.fromisoformat(args.date)]
    elif args.start:
        end = date.fromisoformat(args.end) if args.end else today
        days = list(daterange(date.fromisoformat(args.start), end))
    elif args.backfill:
        days = list(daterange(today - timedelta(days=args.backfill - 1), today))
    else:
        # Default daily run: re-fetch yesterday (late finals / stat corrections) + today.
        days = [today - timedelta(days=1), today]

    years = set()
    for day in days:
        data = collect_day(day)
        path = write_day(data)
        years.add(day.strftime("%Y"))
        print(f"[collect] {day} -> {data['final_games']}/{data['total_games']} final  ({path.relative_to(ROOT)})")

    for year in sorted(years):
        csv_path = rebuild_season_csv(year)
        if csv_path:
            print(f"[collect] season csv -> {csv_path.relative_to(ROOT)}")

    if not args.skip_standings:
        season = max(int(y) for y in years) if years else today.year
        try:
            path = save_standings(season)
            print(f"[collect] standings -> {path.relative_to(ROOT)}")
        except Exception as err:  # standings are non-critical
            print(f"[collect] standings failed: {err}")


if __name__ == "__main__":
    main()
