"""
fetch_eliminatorias.py
=======================
Consulta football-data.org y actualiza la sección "eliminatorias"
de json/resultados.json cruzando por nombre de equipos.

Los cruces de 16avos son conocidos. Octavos en adelante se resuelven
dinámicamente a medida que se cargan los resultados anteriores.

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
COMPETITION = "WC"

RESULTADOS_PATH    = "json/resultados.json"
ELIMINATORIAS_PATH = "json/eliminatorias.json"

STATUS_FINISHED = {"FINISHED"}

STAGES_KO = {
    "LAST_16", "QUARTER_FINALS", "SEMI_FINALS",
    "THIRD_PLACE", "FINAL"
}

# ── MAPEO nombres API → español ───────────────────────────────
TEAM_MAP = {
    "Mexico":                          "México",
    "South Africa":                    "Sudáfrica",
    "Korea Republic":                  "Corea del Sur",
    "South Korea":                     "Corea del Sur",
    "Czechia":                         "Rep. Checa",
    "Czech Republic":                  "Rep. Checa",
    "Rep. Checa":                      "Rep. Checa",
    "Canada":                          "Canadá",
    "Canadá ":                         "Canadá",
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
    "Cape Verde Islands":              "Cabo Verde",
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

# ── CRUCES CONOCIDOS DE 16AVOS (home, away) → match_id ───────
# Basado en los grupos cerrados y terceros clasificados
R16_KNOWN = {
    ("Sudáfrica",      "Canadá"):        "k73",
    ("Alemania",       "Paraguay"):      "k74",
    ("Países Bajos",   "Marruecos"):     "k75",
    ("Brasil",         "Japón"):         "k76",
    ("Francia",        "Suecia"):        "k77",
    ("Costa de Marfil","Noruega"):       "k78",
    ("México",         "Ecuador"):       "k79",
    ("Inglaterra",     "RD Congo"):      "k80",
    ("Estados Unidos", "Bosnia y Herz."):"k81",
    ("Bélgica",        "Senegal"):       "k82",
    ("Portugal",       "Croacia"):       "k83",
    ("España",         "Austria"):       "k84",
    ("Suiza",          "Argelia"):       "k85",
    ("Argentina",      "Cabo Verde"):    "k86",
    ("Colombia",       "Ghana"):         "k87",
    ("Australia",      "Egipto"):        "k88",
}

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

def extract_score(match):
    score  = match.get("score", {})
    reg    = score.get("regularTime", {})
    ft     = score.get("fullTime", {})
    base_h = reg.get("home") if reg.get("home") is not None else ft.get("home")
    base_a = reg.get("away") if reg.get("away") is not None else ft.get("away")
    pen    = score.get("penalties", {})
    pen_h  = pen.get("home")
    pen_a  = pen.get("away")
    return base_h, base_a, pen_h, pen_a

def resolve_winner(match_id, resultados, eliminatorias_data):
    """Resuelve el ganador de un partido KO ya jugado."""
    sc = resultados.get("eliminatorias", {}).get(match_id)
    if not sc or sc.get("scoreH") is None:
        return None

    # Buscar los equipos de ese partido en el índice dinámico
    home = resultados.get("_teams", {}).get(match_id, {}).get("home")
    away = resultados.get("_teams", {}).get(match_id, {}).get("away")
    if not home or not away:
        return None

    h, a = sc["scoreH"], sc["scoreA"]
    if h > a:
        return home
    if a > h:
        return away
    # Empate → penales
    if sc.get("penH") is not None:
        return home if sc["penH"] > sc["penA"] else away
    return None

def resolve_loser(match_id, resultados):
    """Resuelve el perdedor de un partido KO ya jugado."""
    sc = resultados.get("eliminatorias", {}).get(match_id)
    if not sc or sc.get("scoreH") is None:
        return None
    home = resultados.get("_teams", {}).get(match_id, {}).get("home")
    away = resultados.get("_teams", {}).get(match_id, {}).get("away")
    if not home or not away:
        return None
    h, a = sc["scoreH"], sc["scoreA"]
    if h > a:
        return away
    if a > h:
        return home
    if sc.get("penH") is not None:
        return away if sc["penH"] > sc["penA"] else home
    return None

def build_dynamic_lookup(resultados):
    """
    Construye el lookup dinámico para octavos en adelante
    basándose en los ganadores de 16avos ya registrados en _teams.
    """
    lookup = {}

    def add(home, away, mid):
        if home and away:
            lookup[(home, away)] = mid
            lookup[(away, home)] = mid  # también invertido por si la API los invierte

    # Octavos — ganadores de 16avos
    # P89: G.P74 vs G.P77
    w74 = resolve_winner("k74", resultados, None)
    w77 = resolve_winner("k77", resultados, None)
    add(w74, w77, "k89")

    # P90: G.P73 vs G.P75
    w73 = resolve_winner("k73", resultados, None)
    w75 = resolve_winner("k75", resultados, None)
    add(w73, w75, "k90")

    # P91: G.P76 vs G.P78
    w76 = resolve_winner("k76", resultados, None)
    w78 = resolve_winner("k78", resultados, None)
    add(w76, w78, "k91")

    # P92: G.P79 vs G.P80
    w79 = resolve_winner("k79", resultados, None)
    w80 = resolve_winner("k80", resultados, None)
    add(w79, w80, "k92")

    # P93: G.P83 vs G.P84
    w83 = resolve_winner("k83", resultados, None)
    w84 = resolve_winner("k84", resultados, None)
    add(w83, w84, "k93")

    # P94: G.P81 vs G.P82
    w81 = resolve_winner("k81", resultados, None)
    w82 = resolve_winner("k82", resultados, None)
    add(w81, w82, "k94")

    # P95: G.P86 vs G.P88
    w86 = resolve_winner("k86", resultados, None)
    w88 = resolve_winner("k88", resultados, None)
    add(w86, w88, "k95")

    # P96: G.P85 vs G.P87
    w85 = resolve_winner("k85", resultados, None)
    w87 = resolve_winner("k87", resultados, None)
    add(w85, w87, "k96")

    # Cuartos — ganadores de octavos
    w89 = resolve_winner("k89", resultados, None)
    w90 = resolve_winner("k90", resultados, None)
    add(w89, w90, "k97")

    w93 = resolve_winner("k93", resultados, None)
    w94 = resolve_winner("k94", resultados, None)
    add(w93, w94, "k98")

    w91 = resolve_winner("k91", resultados, None)
    w92 = resolve_winner("k92", resultados, None)
    add(w91, w92, "k99")

    w95 = resolve_winner("k95", resultados, None)
    w96 = resolve_winner("k96", resultados, None)
    add(w95, w96, "k100")

    # Semis — ganadores de cuartos
    w97 = resolve_winner("k97", resultados, None)
    w98 = resolve_winner("k98", resultados, None)
    add(w97, w98, "k101")

    w99  = resolve_winner("k99",  resultados, None)
    w100 = resolve_winner("k100", resultados, None)
    add(w99, w100, "k102")

    # 3er puesto — perdedores de semis
    l101 = resolve_loser("k101", resultados)
    l102 = resolve_loser("k102", resultados)
    add(l101, l102, "k103")

    # Final — ganadores de semis
    w101 = resolve_winner("k101", resultados, None)
    w102 = resolve_winner("k102", resultados, None)
    add(w101, w102, "k104")

    return lookup

def main():
    print(f"🕐 {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("📡 [Eliminatorias] Consultando football-data.org...")

    token      = get_token()
    api_data   = fetch_matches(token)
    resultados = load_json(RESULTADOS_PATH)

    resultados.setdefault("partidos", {})
    resultados.setdefault("eliminatorias", {})
    resultados.setdefault("terceros", {})
    # _teams guarda los equipos de cada partido KO para resolver la llave
    resultados.setdefault("_teams", {})

    matches = api_data.get("matches", [])

    ko_matches = [
        m for m in matches
        if m.get("stage") in STAGES_KO and m.get("status") in STATUS_FINISHED
    ]

    print(f"📋 Partidos KO finalizados en API: {len(ko_matches)}")

    if not ko_matches:
        print("ℹ️  No hay partidos de eliminatorias finalizados todavía")
        return

    # Construir lookup dinámico (octavos en adelante)
    dynamic_lookup = build_dynamic_lookup(resultados)

    updated = 0

    for match in ko_matches:
        stage     = match.get("stage", "")
        home_name = normalize(match.get("homeTeam", {}).get("name", ""))
        away_name = normalize(match.get("awayTeam", {}).get("name", ""))
        base_h, base_a, pen_h, pen_a = extract_score(match)

        if base_h is None or base_a is None:
            print(f"  ⚠️  Sin score: {home_name} vs {away_name}")
            continue

        # Buscar match_id — primero en 16avos conocidos, luego en dinámico
        match_id = R16_KNOWN.get((home_name, away_name)) or \
                   R16_KNOWN.get((away_name, home_name)) or \
                   dynamic_lookup.get((home_name, away_name))

        if not match_id:
            print(f"  ⚠️  Sin mapeo: {home_name} vs {away_name} [{stage}]")
            continue

        result = {"scoreH": base_h, "scoreA": base_a}
        if pen_h is not None and pen_a is not None:
            result["penH"] = pen_h
            result["penA"] = pen_a

        pen_str  = f" (pen {pen_h}-{pen_a})" if "penH" in result else ""
        existing = resultados["eliminatorias"].get(match_id, {})

        if existing != result:
            resultados["eliminatorias"][match_id] = result
            # Guardar los equipos para resolver la llave siguiente
            resultados["_teams"][match_id] = {"home": home_name, "away": away_name}
            print(f"  ✅ [{stage}] {home_name} {base_h}-{base_a} {away_name}{pen_str} → {match_id}")
            updated += 1
        else:
            # Asegurarse de que _teams esté actualizado aunque el resultado no cambie
            if match_id not in resultados["_teams"]:
                resultados["_teams"][match_id] = {"home": home_name, "away": away_name}
                updated += 1  # forzar guardado para persistir _teams
            print(f"  ℹ️  Sin cambios: {home_name} vs {away_name}")

    print(f"\n📊 Eliminatorias actualizadas: {updated}")

    if updated > 0:
        save_json(RESULTADOS_PATH, resultados)
        print(f"💾 {RESULTADOS_PATH} guardado")
    else:
        print("ℹ️  Sin cambios en eliminatorias")

if __name__ == "__main__":
    main()