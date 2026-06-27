"""
fetch_eliminatorias.py
=======================
Consulta football-data.org y actualiza SOLO la sección
"eliminatorias" de json/resultados.json con los resultados
de los partidos de fase eliminatoria del Mundial 2026.

Script separado de fetch_resultados.py para no interferir
con la lógica de fase de grupos.

Requiere variable de entorno: FOOTBALL_DATA_TOKEN
"""

import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

# ── CONFIGURACIÓN ────────────────────────────────────────────
API_BASE    = "https://api.football-data.org/v4"
COMPETITION = "WC"

RESULTADOS_PATH    = "json/resultados.json"
ELIMINATORIAS_PATH = "json/eliminatorias.json"

STATUS_FINISHED = {"FINISHED"}

# Stages KO que devuelve la API
STAGES_KO = {
    "LAST_16", "QUARTER_FINALS", "SEMI_FINALS",
    "THIRD_PLACE", "FINAL"
}

# ── MAPEO nombres API (inglés) → nombres en eliminatorias ────
TEAM_MAP = {
    "Mexico":                          "México",
    "South Africa":                    "Sudáfrica",
    "Korea Republic":                  "Corea del Sur",
    "South Korea":                     "Corea del Sur",
    "Czechia":                         "Rep. Checa",
    "Czech Republic":                  "Rep. Checa",
    "Rep. Checa":                      "Rep. Checa",
    "Canada":                          "Canadá",
    "Canadá":                          "Canadá",
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
    """
    Devuelve (base_h, base_a, pen_h, pen_a).
    base = resultado al 90min (sin penales).
    pen  = resultado de la tanda si la hubo.
    """
    score = match.get("score", {})

    reg   = score.get("regularTime", {})
    reg_h = reg.get("home")
    reg_a = reg.get("away")

    ft    = score.get("fullTime", {})
    ft_h  = ft.get("home")
    ft_a  = ft.get("away")

    base_h = reg_h if reg_h is not None else ft_h
    base_a = reg_a if reg_a is not None else ft_a

    pen   = score.get("penalties", {})
    pen_h = pen.get("home")
    pen_a = pen.get("away")

    return base_h, base_a, pen_h, pen_a

def build_ko_date_lookup(eliminatorias):
    """
    Índice: fecha (YYYY-MM-DD, hora Argentina) → lista de partidos KO.
    Usamos la fecha del JSON que está en hora Argentina.
    """
    lookup = {}
    for round_ in eliminatorias:
        for m in round_["matches"]:
            lookup.setdefault(m["date"], []).append(m)
    return lookup

def find_ko_match(candidates, api_hour_utc, resultados_ko):
    """
    Dado una lista de candidatos para una fecha, intenta identificar
    el partido correcto por hora (UTC-3 = hora Argentina).
    Devuelve el id del partido o None.
    """
    api_hour_arg = (api_hour_utc - 3) % 24

    # Filtrar los que ya tienen resultado — si todos lo tienen, no hacer nada
    sin_resultado = [c for c in candidates if c["id"] not in resultados_ko]
    if not sin_resultado:
        return None  # todos ya procesados

    # Si hay uno solo sin resultado, ese es
    if len(sin_resultado) == 1:
        return sin_resultado[0]["id"]

    # Si hay varios, cruzar por hora aproximada (tolerancia ±1 hora)
    for c in sin_resultado:
        c_hour = int(c["time"].split(":")[0])
        if abs(api_hour_arg - c_hour) <= 1:
            return c["id"]

    # Fallback: devolver el primero sin resultado
    return sin_resultado[0]["id"]

def main():
    print(f"🕐 {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("📡 [Eliminatorias] Consultando football-data.org...")

    token         = get_token()
    api_data      = fetch_matches(token)
    eliminatorias = load_json(ELIMINATORIAS_PATH)
    resultados    = load_json(RESULTADOS_PATH)

    resultados.setdefault("partidos", {})
    resultados.setdefault("eliminatorias", {})
    resultados.setdefault("terceros", {})

    ko_lookup    = build_ko_date_lookup(eliminatorias)
    matches      = api_data.get("matches", [])

    # Filtrar solo partidos KO terminados
    ko_matches = [
        m for m in matches
        if m.get("stage") in STAGES_KO and m.get("status") in STATUS_FINISHED
    ]

    print(f"📋 Partidos KO finalizados en API: {len(ko_matches)}")

    if not ko_matches:
        print("ℹ️  No hay partidos de eliminatorias finalizados todavía")
        return

    updated = 0

    for match in ko_matches:
        stage     = match.get("stage", "")
        home_name = normalize(match.get("homeTeam", {}).get("name", ""))
        away_name = normalize(match.get("awayTeam", {}).get("name", ""))
        base_h, base_a, pen_h, pen_a = extract_score(match)

        if base_h is None or base_a is None:
            print(f"  ⚠️  Sin score: {home_name} vs {away_name}")
            continue

        # Fecha UTC → buscar en eliminatorias con tolerancia ±1 día
        utc_date_str = match.get("utcDate", "")[:10]
        utc_hour     = int(match.get("utcDate", "T00:00")[11:13])
        utc_dt       = datetime.strptime(utc_date_str, "%Y-%m-%d")

        candidates = []
        for delta in [-1, 0, 1]:
            d = (utc_dt + timedelta(days=delta)).strftime("%Y-%m-%d")
            candidates += ko_lookup.get(d, [])

        if not candidates:
            print(f"  ⚠️  Sin candidatos por fecha: {home_name} vs {away_name} ({utc_date_str})")
            continue

        match_id = find_ko_match(candidates, utc_hour, resultados["eliminatorias"])

        if not match_id:
            print(f"  ℹ️  Ya procesado: {home_name} vs {away_name}")
            continue

        result = {"scoreH": base_h, "scoreA": base_a}
        if pen_h is not None and pen_a is not None:
            result["penH"] = pen_h
            result["penA"] = pen_a

        pen_str  = f" (pen {pen_h}-{pen_a})" if "penH" in result else ""
        existing = resultados["eliminatorias"].get(match_id, {})

        if existing != result:
            resultados["eliminatorias"][match_id] = result
            print(f"  ✅ [{stage}] {home_name} {base_h}-{base_a} {away_name}{pen_str} → {match_id}")
            updated += 1
        else:
            print(f"  ℹ️  Sin cambios: {home_name} vs {away_name}")

    print(f"\n📊 Eliminatorias actualizadas: {updated}")

    if updated > 0:
        save_json(RESULTADOS_PATH, resultados)
        print(f"💾 {RESULTADOS_PATH} guardado")
    else:
        print("ℹ️  Sin cambios en eliminatorias")

if __name__ == "__main__":
    main()
