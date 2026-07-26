"""Build the static site in docs/ from the collected JSON in data/."""

from __future__ import annotations

import html
import json
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
GAMES_DIR = DATA / "games"
DOCS = ROOT / "docs"

CSS = """
:root {
  --bg: #0d1117; --panel: #161b22; --panel-2: #1c2230; --line: #2a3240;
  --text: #e6edf3; --muted: #8b98a9; --accent: #d7382b; --accent-2: #1f6feb;
  --win: #3fb950;
}
@media (prefers-color-scheme: light) {
  :root { --bg:#f4f6f9; --panel:#fff; --panel-2:#f0f3f7; --line:#dde3ea;
          --text:#12161c; --muted:#5b6675; --win:#1a7f37; }
}
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--text);
  font:16px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif; }
a { color: var(--accent-2); text-decoration: none; }
a:hover { text-decoration: underline; }
header.site { background:linear-gradient(120deg,#0b2340,#132f52 60%,var(--accent));
  color:#fff; padding:26px 20px 22px; }
.wrap { max-width: 1080px; margin: 0 auto; padding: 0 20px; }
header.site h1 { margin:0; font-size:1.7rem; letter-spacing:-.02em; }
header.site h1 a { color:#fff; }
header.site p { margin:6px 0 0; opacity:.85; font-size:.92rem; }
nav.datebar { display:flex; gap:8px; flex-wrap:wrap; align-items:center;
  margin:18px auto 0; }
nav.datebar a, .btn { background:rgba(255,255,255,.14); color:#fff; padding:6px 12px;
  border-radius:999px; font-size:.85rem; border:1px solid rgba(255,255,255,.18); }
nav.datebar a:hover { background:rgba(255,255,255,.26); text-decoration:none; }
nav.datebar a.current { background:#fff; color:#0b2340; font-weight:600; }
main { padding: 24px 0 60px; }
.summary { display:flex; gap:14px; flex-wrap:wrap; margin-bottom:20px; }
.stat { background:var(--panel); border:1px solid var(--line); border-radius:10px;
  padding:10px 16px; min-width:110px; }
.stat b { display:block; font-size:1.35rem; }
.stat span { color:var(--muted); font-size:.78rem; text-transform:uppercase; letter-spacing:.05em; }
.games { display:grid; gap:16px; grid-template-columns:repeat(auto-fill,minmax(330px,1fr)); }
.game { background:var(--panel); border:1px solid var(--line); border-radius:12px;
  overflow:hidden; }
.game .head { display:flex; justify-content:space-between; font-size:.75rem;
  color:var(--muted); padding:8px 14px; background:var(--panel-2);
  border-bottom:1px solid var(--line); text-transform:uppercase; letter-spacing:.04em; }
.game .final { color:var(--accent); font-weight:700; }
.teams { padding:6px 14px 10px; }
.team { display:flex; align-items:center; gap:10px; padding:7px 0; }
.team + .team { border-top:1px dashed var(--line); }
.team .logo { width:26px; height:26px; flex:0 0 26px; }
.team .nm { flex:1; font-weight:600; }
.team .rec { color:var(--muted); font-weight:400; font-size:.8rem; margin-left:6px; }
.team .sc { font-variant-numeric:tabular-nums; font-size:1.25rem; font-weight:700;
  min-width:34px; text-align:right; }
.team.w .nm, .team.w .sc { color:var(--win); }
.team.w .sc::after { content:"\\25C0"; font-size:.6rem; margin-left:6px; vertical-align:middle; }
table.line { width:100%; border-collapse:collapse; font-size:.76rem;
  font-variant-numeric:tabular-nums; }
table.line th, table.line td { padding:3px 5px; text-align:center; border-bottom:1px solid var(--line); }
table.line th { color:var(--muted); font-weight:600; }
table.line td.tm, table.line th.tm { text-align:left; font-weight:600; }
table.line td.tot { font-weight:700; background:var(--panel-2); }
.linewrap { padding:0 14px 10px; overflow-x:auto; }
.meta { padding:9px 14px; border-top:1px solid var(--line); font-size:.78rem;
  color:var(--muted); background:var(--panel-2); }
.meta div + div { margin-top:3px; }
.meta b { color:var(--text); font-weight:600; }
.hr-list { margin:3px 0 0; padding-left:16px; }
footer { border-top:1px solid var(--line); color:var(--muted); font-size:.82rem;
  padding:22px 0 40px; }
h2.sec { font-size:1.05rem; text-transform:uppercase; letter-spacing:.06em;
  color:var(--muted); margin:34px 0 12px; }
table.st { width:100%; border-collapse:collapse; background:var(--panel);
  border:1px solid var(--line); border-radius:10px; overflow:hidden; font-size:.88rem; }
table.st th, table.st td { padding:7px 10px; border-bottom:1px solid var(--line); text-align:right; }
table.st th:first-child, table.st td:first-child { text-align:left; }
table.st thead th { background:var(--panel-2); color:var(--muted); font-size:.75rem;
  text-transform:uppercase; letter-spacing:.05em; }
.divgrid { display:grid; gap:18px; grid-template-columns:repeat(auto-fill,minmax(330px,1fr)); }
.divgrid h3 { margin:0 0 8px; font-size:.95rem; }
.empty { background:var(--panel); border:1px dashed var(--line); border-radius:12px;
  padding:40px; text-align:center; color:var(--muted); }
.arch { columns: 3 190px; column-gap:20px; }
.arch a { display:block; padding:3px 0; }
"""

LOGO = "https://www.mlbstatic.com/team-logos/{id}.svg"


def esc(value) -> str:
    return html.escape(str(value if value is not None else ""))


def pretty_date(iso: str) -> str:
    return date.fromisoformat(iso).strftime("%A, %B %-d, %Y")


def short_date(iso: str) -> str:
    return date.fromisoformat(iso).strftime("%b %-d")


def load_days() -> list[dict]:
    days = []
    for path in sorted(GAMES_DIR.rglob("*.json")):
        try:
            days.append(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
    days.sort(key=lambda d: d["date"])
    return days


def linescore_table(game: dict) -> str:
    innings = game.get("innings") or []
    if not innings:
        return ""
    away, home = game["teams"]["away"], game["teams"]["home"]
    nums = [i["num"] for i in innings]
    head = "".join(f"<th>{n}</th>" for n in nums)

    def row(side_key: str, side: dict) -> str:
        cells = ""
        for inn in innings:
            val = inn.get(side_key)
            cells += f"<td>{'' if val is None else val}</td>"
        return (
            f"<tr><td class='tm'>{esc(side['abbr'])}</td>{cells}"
            f"<td class='tot'>{esc(side['score'])}</td>"
            f"<td class='tot'>{esc(side['hits'])}</td>"
            f"<td class='tot'>{esc(side['errors'])}</td></tr>"
        )

    return (
        "<div class='linewrap'><table class='line'><thead><tr>"
        f"<th class='tm'></th>{head}<th>R</th><th>H</th><th>E</th>"
        "</tr></thead><tbody>"
        f"{row('away', away)}{row('home', home)}"
        "</tbody></table></div>"
    )


def game_card(game: dict) -> str:
    away, home = game["teams"]["away"], game["teams"]["home"]
    status = game["status"]
    status_cls = "final" if game["is_final"] else ""

    def team_row(side: dict) -> str:
        win = " w" if game["is_final"] and side.get("is_winner") else ""
        rec = side.get("record") or {}
        rec_txt = f"({rec.get('wins')}-{rec.get('losses')})" if rec.get("wins") is not None else ""
        logo = LOGO.format(id=side["id"]) if side.get("id") else ""
        score = side["score"] if side["score"] is not None else "-"
        return (
            f"<div class='team{win}'>"
            f"<img class='logo' loading='lazy' src='{esc(logo)}' alt=''>"
            f"<span class='nm'>{esc(side['name'])}<span class='rec'>{esc(rec_txt)}</span></span>"
            f"<span class='sc'>{esc(score)}</span></div>"
        )

    dec = game["decisions"]
    meta_bits = []
    if dec.get("winner") or dec.get("loser"):
        parts = []
        if dec.get("winner"):
            parts.append(f"W: <b>{esc(dec['winner'])}</b>")
        if dec.get("loser"):
            parts.append(f"L: <b>{esc(dec['loser'])}</b>")
        if dec.get("save"):
            parts.append(f"SV: <b>{esc(dec['save'])}</b>")
        meta_bits.append("<div>" + " &nbsp;·&nbsp; ".join(parts) + "</div>")
    if not game["is_final"] and (away.get("probable_pitcher") or home.get("probable_pitcher")):
        meta_bits.append(
            f"<div>Probables: {esc(away.get('probable_pitcher') or 'TBD')} vs "
            f"{esc(home.get('probable_pitcher') or 'TBD')}</div>"
        )
    hrs = game.get("home_runs") or []
    if hrs:
        def hr_line(h):
            rbi = h.get("rbi") or 1
            tag = "solo" if rbi <= 1 else ("2-run" if rbi == 2 else ("3-run" if rbi == 3 else "grand slam"))
            return (f"<li>{esc(h['batter'])} &mdash; {tag}, inn {esc(h['inning'])}"
                    f" (off {esc(h['pitcher'])})</li>")
        items = "".join(hr_line(h) for h in hrs[:8])
        meta_bits.append(f"<div>Home runs<ul class='hr-list'>{items}</ul></div>")
    venue_line = esc(game.get("venue") or "")
    extras = []
    if game.get("attendance"):
        extras.append(f"{game['attendance']:,} fans")
    if game.get("duration_minutes"):
        mins = game["duration_minutes"]
        extras.append(f"{mins // 60}:{mins % 60:02d}")
    if extras:
        venue_line += " &nbsp;·&nbsp; " + " &nbsp;·&nbsp; ".join(esc(e) for e in extras)
    if venue_line:
        meta_bits.append(f"<div>{venue_line}</div>")
    series = game.get("series_status")
    if series and series.lower() not in ("season", "regular season"):
        meta_bits.append(f"<div>{esc(series)}</div>")
    meta_bits.append(f"<div><a href='{esc(game['mlb_link'])}'>Gameday &rarr;</a></div>")

    innings_note = ""
    if game["is_final"] and (game.get("innings_played") or 9) != 9:
        innings_note = f" / {game['innings_played']}"

    label = game.get("game_type_label") or ""
    if game.get("double_header") in ("Y", "S") and game.get("game_number"):
        label += f" · G{game['game_number']}"

    return (
        "<article class='game'>"
        f"<div class='head'><span>{esc(label)}</span>"
        f"<span class='{status_cls}'>{esc(status)}{innings_note}</span></div>"
        f"<div class='teams'>{team_row(away)}{team_row(home)}</div>"
        f"{linescore_table(game)}"
        f"<div class='meta'>{''.join(meta_bits)}</div>"
        "</article>"
    )


def page(title: str, body: str, nav: str, subtitle: str, depth: int = 0) -> str:
    prefix = "../" * depth
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="Daily MLB game results, box scores and standings, updated automatically.">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>&#9918;</text></svg>">
<style>{CSS}</style>
</head>
<body>
<header class="site">
  <div class="wrap">
    <h1><a href="{prefix}index.html">&#9918; MLB Daily Results</a></h1>
    <p>{subtitle}</p>
    <nav class="datebar">{nav}</nav>
  </div>
</header>
<main class="wrap">{body}</main>
<footer class="wrap">
  <p>Data: <a href="https://statsapi.mlb.com/api/v1/schedule?sportId=1">MLB Stats API</a>.
  Updated automatically by GitHub Actions. Not affiliated with or endorsed by MLB.</p>
  <p><a href="{prefix}archive.html">Archive</a> &nbsp;·&nbsp;
     <a href="{prefix}standings.html">Standings</a> &nbsp;·&nbsp;
     <a href="{prefix}api/latest.json">JSON API</a></p>
</footer>
</body>
</html>
"""


def build_nav(days: list[dict], current: str | None) -> str:
    recent = days[-8:][::-1]
    links = []
    for day in recent:
        cls = " class='current'" if day["date"] == current else ""
        href = "index.html" if day is days[-1] else f"day/{day['date']}.html"
        links.append(f"<a href='{href}'{cls}>{short_date(day['date'])}</a>")
    links.append("<a href='archive.html'>Archive</a>")
    links.append("<a href='standings.html'>Standings</a>")
    return "".join(links)


def build_nav_for_day(days: list[dict], current: str) -> str:
    recent = days[-8:][::-1]
    links = []
    for day in recent:
        cls = " class='current'" if day["date"] == current else ""
        href = "../index.html" if day is days[-1] else f"../day/{day['date']}.html"
        links.append(f"<a href='{href}'{cls}>{short_date(day['date'])}</a>")
    links.append("<a href='../archive.html'>Archive</a>")
    links.append("<a href='../standings.html'>Standings</a>")
    return "".join(links)


def day_body(day: dict) -> str:
    games = day["games"]
    if not games:
        return (
            f"<h2 class='sec'>{esc(pretty_date(day['date']))}</h2>"
            "<div class='empty'>No games scheduled.</div>"
        )
    finals = [g for g in games if g["is_final"]]
    runs = day.get("total_runs", 0)
    avg = f"{runs / len(finals):.1f}" if finals else "-"
    stats = (
        f"<div class='stat'><b>{len(games)}</b><span>Games</span></div>"
        f"<div class='stat'><b>{len(finals)}</b><span>Final</span></div>"
        f"<div class='stat'><b>{runs}</b><span>Runs</span></div>"
        f"<div class='stat'><b>{avg}</b><span>Runs/Game</span></div>"
    )
    cards = "".join(game_card(g) for g in games)
    return (
        f"<h2 class='sec'>{esc(pretty_date(day['date']))}</h2>"
        f"<div class='summary'>{stats}</div>"
        f"<div class='games'>{cards}</div>"
    )


def build_standings_page(days: list[dict]) -> str:
    path = DATA / "standings.json"
    if not path.exists():
        return "<div class='empty'>Standings not collected yet.</div>"
    data = json.loads(path.read_text(encoding="utf-8"))
    blocks = []
    for div in data["divisions"]:
        rows = ""
        for team in div["teams"]:
            rows += (
                f"<tr><td>{esc(team['team'])}</td><td>{esc(team['wins'])}</td>"
                f"<td>{esc(team['losses'])}</td><td>{esc(team['pct'])}</td>"
                f"<td>{esc(team['games_back'])}</td><td>{esc(team['streak'])}</td></tr>"
            )
        blocks.append(
            f"<div><h3>{esc(div['name'])}</h3><table class='st'><thead><tr>"
            "<th>Team</th><th>W</th><th>L</th><th>PCT</th><th>GB</th><th>STRK</th>"
            f"</tr></thead><tbody>{rows}</tbody></table></div>"
        )
    return (
        f"<h2 class='sec'>{esc(data['season'])} Standings</h2>"
        f"<div class='divgrid'>{''.join(blocks)}</div>"
    )


def build() -> None:
    days = load_days()
    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / "day").mkdir(exist_ok=True)
    (DOCS / "api").mkdir(exist_ok=True)
    (DOCS / ".nojekyll").write_text("", encoding="utf-8")

    if not days:
        (DOCS / "index.html").write_text(
            page("MLB Daily Results", "<div class='empty'>No data collected yet.</div>",
                 "", "Waiting for the first collection run."),
            encoding="utf-8",
        )
        return

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    latest = days[-1]
    subtitle = f"Box scores, line scores and standings · updated {stamp}"

    # Home = latest day
    (DOCS / "index.html").write_text(
        page("MLB Daily Results", day_body(latest), build_nav(days, latest["date"]), subtitle),
        encoding="utf-8",
    )

    # One page per day
    for day in days:
        (DOCS / "day" / f"{day['date']}.html").write_text(
            page(
                f"MLB Results — {pretty_date(day['date'])}",
                day_body(day),
                build_nav_for_day(days, day["date"]),
                subtitle,
                depth=1,
            ),
            encoding="utf-8",
        )

    # Archive
    by_month: dict[str, list[dict]] = {}
    for day in days:
        by_month.setdefault(day["date"][:7], []).append(day)
    sections = []
    for month in sorted(by_month, reverse=True):
        label = datetime.strptime(month, "%Y-%m").strftime("%B %Y")
        links = "".join(
            f"<a href='day/{d['date']}.html'>{short_date(d['date'])} "
            f"<span style='color:var(--muted)'>({d['final_games']} final)</span></a>"
            for d in sorted(by_month[month], reverse=True, key=lambda x: x["date"])
        )
        sections.append(f"<h2 class='sec'>{label}</h2><div class='arch'>{links}</div>")
    (DOCS / "archive.html").write_text(
        page("Archive — MLB Daily Results", "".join(sections), build_nav(days, None), subtitle),
        encoding="utf-8",
    )

    # Standings
    (DOCS / "standings.html").write_text(
        page("Standings — MLB Daily Results", build_standings_page(days),
             build_nav(days, None), subtitle),
        encoding="utf-8",
    )

    # JSON endpoints for the site
    (DOCS / "api" / "latest.json").write_text(
        json.dumps(latest, indent=2) + "\n", encoding="utf-8"
    )
    index = {
        "generated_at_utc": stamp,
        "days": [
            {
                "date": d["date"],
                "games": d["total_games"],
                "final": d["final_games"],
                "json": f"../data/games/{d['date'][:4]}/{d['date']}.json",
            }
            for d in days
        ],
    }
    (DOCS / "api" / "index.json").write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")

    print(f"[build] {len(days)} day pages -> docs/")


if __name__ == "__main__":
    build()
