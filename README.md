# ⚾ MLB Daily Results

Automatically collects **every MLB game result, every day** — full box score detail — and
publishes it as a browsable website plus machine-readable JSON/CSV.

**🌐 Live site:** https://USERNAME.github.io/mlb-daily-results/

---

## What it collects

For each game, per day:

| Field | Detail |
|---|---|
| Score & status | Final score, extra innings, postponements, doubleheader game number |
| Line score | Runs by inning for both teams, plus R / H / E totals |
| Pitchers of record | Winning, losing and saving pitcher |
| Home runs | Batter, pitcher, inning, solo / 2-run / 3-run / grand slam |
| Team records | W-L at the time of the game |
| Game info | Venue, attendance, duration, day/night, weather |
| Flags | No-hitters and perfect games |
| Standings | All six divisions, updated daily (W, L, PCT, GB, streak, run diff) |

Data source: the free, public [MLB Stats API](https://statsapi.mlb.com/api/v1/schedule?sportId=1).
No API key and no third-party packages required — the scripts are pure Python standard library.

## How it works

```
scripts/collect.py     → fetches games, writes data/games/YYYY/YYYY-MM-DD.json + data/csv/YYYY.csv
scripts/build_site.py  → renders data/ into the static site in docs/
.github/workflows/daily.yml → runs both twice a day, commits changes, deploys GitHub Pages
```

The scheduled run happens at **08:10 UTC** (after West Coast games finish) and again at
**16:10 UTC** to pick up late finals and official scoring corrections. Each run re-fetches
yesterday as well as today, so revised results self-heal.

## Repository layout

```
data/
  games/2026/2026-07-25.json   one file per day, full detail
  csv/2026.csv                 one row per completed game, whole season
  standings.json               current division standings
docs/                          the published website (GitHub Pages source)
  index.html                   latest day's scoreboard
  day/YYYY-MM-DD.html          one page per date
  archive.html                 every date collected
  standings.html               division standings
  api/latest.json              latest day as JSON
  api/index.json               index of all collected days
scripts/
  mlb_api.py                   MLB Stats API client
  collect.py                   collection + CSV/standings export
  build_site.py                static site generator
```

## Use the data

```bash
# Latest day, as JSON
curl https://USERNAME.github.io/mlb-daily-results/api/latest.json

# Whole season as CSV (pandas, Excel, whatever)
curl -O https://raw.githubusercontent.com/USERNAME/mlb-daily-results/main/data/csv/2026.csv
```

```python
import pandas as pd
df = pd.read_csv("data/csv/2026.csv")
df.groupby("winner").size().sort_values(ascending=False).head()
```

## Run it locally

```bash
python scripts/collect.py                        # yesterday + today
python scripts/collect.py --date 2026-07-04      # one specific date
python scripts/collect.py --backfill 30          # last 30 days
python scripts/collect.py --start 2026-03-26 --end 2026-10-01   # a range
python scripts/build_site.py                     # rebuild docs/
python -m http.server -d docs 8000               # preview at localhost:8000
```

Backfilling an entire season is one command:

```bash
python scripts/collect.py --start 2026-03-26 --end 2026-07-26 && python scripts/build_site.py
```

## Setup notes

Pages is served from the `docs/` folder on the default branch (Settings → Pages → *Deploy from
a branch* → `main` / `/docs`), and the workflow also pushes a Pages artifact so either
deployment mode works. The workflow needs **Settings → Actions → General → Workflow
permissions → Read and write**.

## License

MIT for the code. Game data belongs to MLB Advanced Media; this project is not affiliated with
or endorsed by MLB.
