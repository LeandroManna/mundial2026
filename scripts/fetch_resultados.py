"""
fetch_resultados.py
====================
Consulta football-data.org (API gratuita) y actualiza
json/resultados.json con los resultados del Mundial 2026.

Requiere variable de entorno: FOOTBALL_DATA_TOKEN
"""

import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone

# ── CONFIGURACIÓN ────────────────────────────────────────────
API_BASE    = "https://api.football-data.org/v4"
COMPETITION = "WC"   # FIFA World Cup

RESULTADOS_PATH = "json/resultados.json"
PARTIDOS_PATH   = "json/partidos.json"

STATUS_FINISHED = {"FINISHED"}

# ── MAPEO nombres API (inglés) → nombres en partidos.json ────
TEAM_MAP = {
    "Mexico":                          "México",
    "South Africa":                    "Sudáfrica",
    "Korea Republic":                  "Corea del Sur",
    "South Korea":                     "Corea del Sur",
    "Czechia":                         "Rep. Checa",
    "Czech Republic":                  "Rep. Checa",
    "Rep. Checa":                      "Rep. Checa",
    "Canada":                          "Canadá",
    "Canadá ":                          "Canadá",
    "Bosnia and Herzegovina":          "Bosnia y Herz.",
    "Bosnia-Herzegovina":              "Bosnia y Herz.",
    "Qatar":                           "Qatar",
    "Switzerland":                     "Suiza",
    "Brazil":                          "Brasil",
    "Morocco":                         "Marruecos",
    "Haiti":                           "Haití",
    "Scotland":                        "Escocia",
    "United States":                   "Estados Unidos",
    "Paraguay":                        "Paraguay",
    "Australia":                       "Australia",
    "Türkiye":                         "Turquía",
    "Turkey":                          "Turquía",
    "Germany":                         "Alemania",
    "Curaçao":                         "Curazao",
    "Ivory Coast":                     "Costa de Marfil",
    "Ecuador":                         "Ecuador",
    "Netherlands":                     "Países Bajos",
    "Japan":                           "Japón",
    "Sweden":                          "Suecia",
    "Tunisia":                         "Túnez",
    "Spain":                           "España",
    "Cape Verde Islands":          "Cabo Verde",
    "Cape Verde":                      "Cabo Verde",
    "Saudi Arabia":                    "Arabia Saudita",
    "Uruguay":                         "Uruguay",
    "Iran":                            "Irán",
    "New Zealand":                     "Nueva Zelanda",
    "Belgium":                         "Bélgica",
    "Egypt":                           "Egipto",
    "France":                          "Francia",
    "Senegal":                         "Senegal",
    "Iraq":                            "Irak",
    "Norway":                          "Noruega",
    "Argentina":                       "Argentina",
    "Algeria":                         "Argelia",
    "Austria":                         "Austria",
    "Jordan":                          "Jordania",
    "Portugal":                        "Portugal",
    "DR Congo":                        "RD Congo",
    "Congo DR":                        "RD Congo",
    "Uzbekistan":                      "Uzbekistán",
    "Colombia":                        "Colombia",
    "England":                         "Inglaterra",
    "Croatia":                         "Croacia",
    "Ghana":                           "Ghana",
    "Panama":                          "Panamá",
}

def normalize(name):
    return TEAM_MAP.get(name, name)

def get_token():
    token = os.environ.get("FOOTBALL_DATA_TOKEN", "").strip()
    if not token:
        print("❌ Variable FOOTBALL_DATA_TOKEN no encontrada")
        sys.exit(1)
    return token

def fetch_matches(token):
    url = f"{API_BASE}/competitions/{COMPETITION}/matches"
    req = urllib.request.Request(url, headers={
        "X-Auth-Token": token,
        "Accept":       "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")[:400]
        print(f"❌ HTTP {e.code}: {e.reason}")
        print(f"   {body}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def build_lookup(partidos):
    lookup = {}
    for m in partidos:
        lookup[(m["home"], m["away"])] = m["id"]
    return lookup

def main():
    print(f"🕐 {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("📡 Consultando football-data.org...")

    token      = get_token()
    api_data   = fetch_matches(token)
    partidos   = load_json(PARTIDOS_PATH)
    resultados = load_json(RESULTADOS_PATH)

    resultados.setdefault("partidos", {})
    resultados.setdefault("eliminatorias", {})
    resultados.setdefault("terceros", {})

    lookup  = build_lookup(partidos)
    matches = api_data.get("matches", [])

    print(f"📋 Partidos en API: {len(matches)}")

    updated = 0
    skipped = 0

    for match in matches:
        status = match.get("status", "")

        if status not in STATUS_FINISHED:
            skipped += 1
            continue

        home_name = normalize(match.get("homeTeam", {}).get("name", ""))
        away_name = normalize(match.get("awayTeam", {}).get("name", ""))

        if not home_name or not away_name:
            continue

        # Buscar en nuestro fixture
        match_id = lookup.get((home_name, away_name))
        if not match_id:
            match_id = lookup.get((away_name, home_name))
            if match_id:
                home_name, away_name = away_name, home_name

        if not match_id:
            print(f"  ⚠️  Sin mapeo: {home_name} vs {away_name}")
            continue

        # Scores — fullTime es el resultado final (incluye ET si la hubo)
        score    = match.get("score", {})
        ft       = score.get("fullTime", {})
        score_h  = ft.get("home")
        score_a  = ft.get("away")

        if score_h is None or score_a is None:
            continue

        # Regulation time (90 min) para mostrar el score real antes de penales
        reg      = score.get("regularTime", {})
        reg_h    = reg.get("home")
        reg_a    = reg.get("away")

        # Si hay regularTime usamos ese como score base (penales van aparte)
        base_h = reg_h if reg_h is not None else score_h
        base_a = reg_a if reg_a is not None else score_a

        result = {"scoreH": base_h, "scoreA": base_a}

        # Penales
        pen   = score.get("penalties", {})
        pen_h = pen.get("home")
        pen_a = pen.get("away")
        if pen_h is not None and pen_a is not None:
            result["penH"] = pen_h
            result["penA"] = pen_a

        existing = resultados["partidos"].get(match_id, {})
        if existing != result:
            resultados["partidos"][match_id] = result
            pen_str = f" (pen {pen_h}-{pen_a})" if "penH" in result else ""
            print(f"  ✅ {home_name} {base_h}-{base_a} {away_name}{pen_str}")
            updated += 1

    print(f"\n📊 Actualizados: {updated} | Pendientes: {skipped}")

    if updated > 0:
        save_json(RESULTADOS_PATH, resultados)
        print(f"💾 {RESULTADOS_PATH} guardado")
    else:
        print("ℹ️  Sin cambios")

if __name__ == "__main__":
    main()
