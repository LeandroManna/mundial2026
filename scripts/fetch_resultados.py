"""
fetch_resultados.py
====================
Consulta la API de Olé (Opta) del Mundial 2026 y actualiza
json/resultados.json con los resultados finales de cada partido.

Corre como GitHub Action — no requiere intervención manual.
"""

import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone

# ── CONFIGURACIÓN ────────────────────────────────────────────
API_URL = (
    "https://www.ole.com.ar/stats/soccer/WOC/api/statssapi/"
    "tournament-calendar/873cbl9cd9butm4air0mugxzo/matches/"
    "status/all?pgSz=700"
)

# Ruta al JSON de resultados (relativa a la raíz del repo)
RESULTADOS_PATH = "json/resultados.json"
PARTIDOS_PATH   = "json/partidos.json"

# matchStatus que indica partido finalizado
STATUS_PLAYED = {"Played", "PostMatch"}

# ── MAPEO nombres Opta → nombres en partidos.json ────────────
# La API devuelve nombres en inglés, el proyecto los tiene en español
TEAM_MAP = {
    "Mexico":           "México",
    "South Africa":     "Sudáfrica",
    "South Korea":      "Corea del Sur",
    "Czech Republic":   "Rep. Checa",
    "Canada":           "Canadá",
    "Bosnia-Herzegovina": "Bosnia y Herz.",
    "Bosnia and Herzegovina": "Bosnia y Herz.",
    "Qatar":            "Qatar",
    "Switzerland":      "Suiza",
    "Brazil":           "Brasil",
    "Morocco":          "Marruecos",
    "Haiti":            "Haití",
    "Scotland":         "Escocia",
    "United States":    "Estados Unidos",
    "USA":              "Estados Unidos",
    "Paraguay":         "Paraguay",
    "Australia":        "Australia",
    "Turkey":           "Turquía",
    "Germany":          "Alemania",
    "Curaçao":          "Curazao",
    "Curacao":          "Curazao",
    "Ivory Coast":      "Costa de Marfil",
    "Côte d'Ivoire":    "Costa de Marfil",
    "Ecuador":          "Ecuador",
    "Netherlands":      "Países Bajos",
    "Japan":            "Japón",
    "Sweden":           "Suecia",
    "Tunisia":          "Túnez",
    "Spain":            "España",
    "Cape Verde":       "Cabo Verde",
    "Saudi Arabia":     "Arabia Saudita",
    "Uruguay":          "Uruguay",
    "Iran":             "Irán",
    "New Zealand":      "Nueva Zelanda",
    "Belgium":          "Bélgica",
    "Egypt":            "Egipto",
    "France":           "Francia",
    "Senegal":          "Senegal",
    "Iraq":             "Irak",
    "Norway":           "Noruega",
    "Argentina":        "Argentina",
    "Algeria":          "Argelia",
    "Austria":          "Austria",
    "Jordan":           "Jordania",
    "Portugal":         "Portugal",
    "DR Congo":         "RD Congo",
    "Democratic Republic of Congo": "RD Congo",
    "Uzbekistan":       "Uzbekistán",
    "Colombia":         "Colombia",
    "England":          "Inglaterra",
    "Croatia":          "Croacia",
    "Ghana":            "Ghana",
    "Panama":           "Panamá",
}

def normalize(name: str) -> str:
    return TEAM_MAP.get(name, name)


def fetch_api() -> dict:
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; Mundial2026Bot/1.0)",
        "Accept":     "application/json",
    }
    req = urllib.request.Request(API_URL, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"❌ HTTP {e.code}: {e.reason}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error consultando API: {e}")
        sys.exit(1)


def load_json(path: str) -> dict | list:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def build_lookup(partidos: list) -> dict:
    """
    Crea un índice: (home_normalizado, away_normalizado) → id del partido
    para cruzar con los datos de la API.
    """
    lookup = {}
    for m in partidos:
        key = (m["home"], m["away"])
        lookup[key] = m["id"]
    return lookup


def main():
    print(f"🕐 {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("📡 Consultando API de Olé...")

    api_data   = fetch_api()
    partidos   = load_json(PARTIDOS_PATH)
    resultados = load_json(RESULTADOS_PATH)

    if "partidos" not in resultados:
        resultados["partidos"] = {}
    if "eliminatorias" not in resultados:
        resultados["eliminatorias"] = {}
    if "terceros" not in resultados:
        resultados["terceros"] = {}

    lookup   = build_lookup(partidos)
    matches  = api_data.get("data", {}).get("match", [])

    updated  = 0
    skipped  = 0

    for match in matches:
        info = match.get("matchInfo", {})
        live = match.get("liveData", {})
        details = live.get("matchDetails", {})

        status = details.get("matchStatus", "")
        if status not in STATUS_PLAYED:
            skipped += 1
            continue

        # Obtener equipos
        contestants = info.get("contestant", [])
        home_name = away_name = None
        for c in contestants:
            name = normalize(c.get("name", ""))
            if c.get("position") == "home":
                home_name = name
            elif c.get("position") == "away":
                away_name = name

        if not home_name or not away_name:
            continue

        # Buscar el partido en nuestro JSON
        match_id = lookup.get((home_name, away_name))
        if not match_id:
            # Intentar invertido (no debería pasar pero por las dudas)
            match_id = lookup.get((away_name, home_name))
            if match_id:
                home_name, away_name = away_name, home_name

        if not match_id:
            print(f"  ⚠️  No encontrado: {home_name} vs {away_name}")
            continue

        # Scores finales (ft = full time)
        scores = details.get("scores", {})
        ft     = scores.get("ft", scores.get("total", {}))
        score_h = ft.get("home")
        score_a = ft.get("away")

        if score_h is None or score_a is None:
            continue

        result = {"scoreH": score_h, "scoreA": score_a}

        # Penales — si el partido terminó empatado y hay score de penales
        pen = scores.get("pen", {})
        if pen:
            pen_h = pen.get("home")
            pen_a = pen.get("away")
            if pen_h is not None and pen_a is not None:
                result["penH"] = pen_h
                result["penA"] = pen_a

        # Solo actualizar si cambió algo
        existing = resultados["partidos"].get(match_id, {})
        if existing != result:
            resultados["partidos"][match_id] = result
            pen_str = f" (pen {result.get('penH')}-{result.get('penA')})" if "penH" in result else ""
            print(f"  ✅ {home_name} {score_h}-{score_a} {away_name}{pen_str}")
            updated += 1

    print(f"\n📊 Resultado: {updated} actualizados, {skipped} pendientes")

    if updated > 0:
        save_json(RESULTADOS_PATH, resultados)
        print(f"💾 {RESULTADOS_PATH} guardado")
    else:
        print("ℹ️  Sin cambios — no se escribe el archivo")

    # Exit code 0 siempre — el workflow decide si hacer commit
    # basándose en si el archivo cambió (git diff)
    sys.exit(0)


if __name__ == "__main__":
    main()
