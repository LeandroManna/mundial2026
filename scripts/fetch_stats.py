"""
fetch_stats.py
==============
Consulta football-data.org y genera json/stats.json con estadisticas
del Mundial 2026 para la pestana Estadisticas del sitio.

Requiere variable de entorno: FOOTBALL_DATA_TOKEN
"""

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

API_BASE = "https://api.football-data.org/v4"
COMPETITION = "WC"
STATS_PATH = "json/stats.json"

TEAM_MAP = {
    "Mexico": "México",
    "South Africa": "Sudáfrica",
    "Korea Republic": "Corea del Sur",
    "South Korea": "Corea del Sur",
    "Czechia": "Rep. Checa",
    "Czech Republic": "Rep. Checa",
    "Canada": "Canadá",
    "Bosnia and Herzegovina": "Bosnia y Herz.",
    "Bosnia-Herzegovina": "Bosnia y Herz.",
    "Qatar": "Qatar",
    "Switzerland": "Suiza",
    "Brazil": "Brasil",
    "Morocco": "Marruecos",
    "Haiti": "Haití",
    "Scotland": "Escocia",
    "United States": "Estados Unidos",
    "Paraguay": "Paraguay",
    "Australia": "Australia",
    "Türkiye": "Turquía",
    "Turkey": "Turquía",
    "Germany": "Alemania",
    "Curaçao": "Curazao",
    "Ivory Coast": "Costa de Marfil",
    "Ecuador": "Ecuador",
    "Netherlands": "Países Bajos",
    "Japan": "Japón",
    "Sweden": "Suecia",
    "Tunisia": "Túnez",
    "Spain": "España",
    "Cape Verde Islands": "Cabo Verde",
    "Cape Verde": "Cabo Verde",
    "Saudi Arabia": "Arabia Saudita",
    "Uruguay": "Uruguay",
    "Iran": "Irán",
    "New Zealand": "Nueva Zelanda",
    "Belgium": "Bélgica",
    "Egypt": "Egipto",
    "France": "Francia",
    "Senegal": "Senegal",
    "Iraq": "Irak",
    "Norway": "Noruega",
    "Argentina": "Argentina",
    "Algeria": "Argelia",
    "Austria": "Austria",
    "Jordan": "Jordania",
    "Portugal": "Portugal",
    "DR Congo": "RD Congo",
    "Congo DR": "RD Congo",
    "Uzbekistan": "Uzbekistán",
    "Colombia": "Colombia",
    "England": "Inglaterra",
    "Croatia": "Croacia",
    "Ghana": "Ghana",
    "Panama": "Panamá",
}


def normalize_team(name):
    return TEAM_MAP.get(name, name)


def get_token():
    token = os.environ.get("FOOTBALL_DATA_TOKEN", "").strip()
    if not token:
        print("ERROR: Variable FOOTBALL_DATA_TOKEN no encontrada")
        sys.exit(1)
    return token


def fetch(path, token):
    url = f"{API_BASE}{path}"
    req = urllib.request.Request(
        url,
        headers={
            "X-Auth-Token": token,
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")[:400]
        raise RuntimeError(f"HTTP {e.code}: {e.reason} - {body}") from e


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def build_scorers(token):
    data = fetch(f"/competitions/{COMPETITION}/scorers?limit=10", token)
    scorers = []
    for idx, item in enumerate(data.get("scorers", [])[:10], start=1):
        player = item.get("player", {})
        team = item.get("team", {})
        goals = item.get("goals") or 0
        assists = item.get("assists") or 0
        scorers.append(
            {
                "rank": idx,
                "player": player.get("name", "?"),
                "team": normalize_team(team.get("name", "?")),
                "playedMatches": item.get("playedMatches") or 0,
                "goals": goals,
                "assists": assists,
                "goalContributions": goals + assists,
                "penalties": item.get("penalties") or 0,
            }
        )
    return scorers


def score_without_penalties(match):
    score = match.get("score", {})
    duration = score.get("duration")

    if duration == "REGULAR":
        full = score.get("fullTime", {})
        return full.get("home") or 0, full.get("away") or 0

    if duration in ("EXTRA_TIME", "PENALTY_SHOOTOUT"):
        regular = score.get("regularTime", {})
        extra = score.get("extraTime", {})
        home = (regular.get("home") or 0) + (extra.get("home") or 0)
        away = (regular.get("away") or 0) + (extra.get("away") or 0)
        return home, away

    full = score.get("fullTime", {})
    return full.get("home") or 0, full.get("away") or 0


def build_team_ranking(token):
    data = fetch(f"/competitions/{COMPETITION}/matches", token)
    stats = {}

    def init_team(name):
        if name not in stats:
            stats[name] = {
                "team": name,
                "pj": 0,
                "pg": 0,
                "pe": 0,
                "pp": 0,
                "gf": 0,
                "gc": 0,
                "dg": 0,
                "win_pct": 0.0,
                "avg_gf": 0.0,
                "avg_gc": 0.0,
            }

    for match in data.get("matches", []):
        if match.get("status") != "FINISHED":
            continue

        home = normalize_team(match.get("homeTeam", {}).get("name"))
        away = normalize_team(match.get("awayTeam", {}).get("name"))
        if not home or not away:
            continue

        init_team(home)
        init_team(away)

        home_gf, away_gf = score_without_penalties(match)
        winner = match.get("score", {}).get("winner")

        stats[home]["pj"] += 1
        stats[away]["pj"] += 1
        stats[home]["gf"] += home_gf
        stats[home]["gc"] += away_gf
        stats[away]["gf"] += away_gf
        stats[away]["gc"] += home_gf

        if winner == "HOME_TEAM":
            stats[home]["pg"] += 1
            stats[away]["pp"] += 1
        elif winner == "AWAY_TEAM":
            stats[away]["pg"] += 1
            stats[home]["pp"] += 1
        elif winner == "DRAW":
            stats[home]["pe"] += 1
            stats[away]["pe"] += 1

    ranking = list(stats.values())
    for item in ranking:
        item["dg"] = item["gf"] - item["gc"]
        if item["pj"] > 0:
            item["win_pct"] = round((item["pg"] / item["pj"]) * 100, 1)
            item["avg_gf"] = round(item["gf"] / item["pj"], 2)
            item["avg_gc"] = round(item["gc"] / item["pj"], 2)

    ranking.sort(
        key=lambda x: (
            x["win_pct"],
            x["dg"],
            x["avg_gf"],
            x["gf"],
            -x["gc"],
        ),
        reverse=True,
    )

    for idx, item in enumerate(ranking, start=1):
        item["rank"] = idx

    return ranking


def build_competition_info(token):
    data = fetch(f"/competitions/{COMPETITION}", token)
    season = data.get("currentSeason", {})
    return {
        "name": data.get("name"),
        "code": data.get("code"),
        "startDate": season.get("startDate"),
        "endDate": season.get("endDate"),
        "currentMatchday": season.get("currentMatchday"),
        "lastUpdated": data.get("lastUpdated"),
    }


def main():
    token = get_token()
    print("Consultando estadisticas de football-data.org...")

    out = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": "football-data.org",
        "competition": build_competition_info(token),
        "scorers": build_scorers(token),
        "teamRanking": build_team_ranking(token),
    }

    save_json(STATS_PATH, out)
    print(f"{STATS_PATH} actualizado")
    print(f"Goleadores: {len(out['scorers'])}")
    print(f"Equipos: {len(out['teamRanking'])}")


if __name__ == "__main__":
    main()

