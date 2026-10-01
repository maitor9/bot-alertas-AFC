import re
import requests


# ==========================================
# ⚽ SCRAPER DE FÚTBOL EN VIVO (ESPN API)
# ==========================================
async def extraer_futbol_en_vivo():
  partidos_candidatos = []
  print("⏳ Consultando API pública de ESPN en vivo...", flush=True)

  try:
    url = "https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard"
    response = requests.get(url, timeout=12)

    if response.status_code == 200:
      data = response.json()
      events = data.get("events", [])

      for event in events:
        try:
          status = event.get("status", {})
          state = status.get("type", {}).get("state", "")

          # Solo procesamos partidos que estén en juego ("in")
          if state != "in":
            continue

          # Extraer el minuto actual del partido
          display_clock = status.get("displayClock", "50")
          min_int = 50
          match_min = re.search(r"\d+", str(display_clock))
          if match_min:
            min_int = int(match_min.group())

          competitions = event.get("competitions", [])
          if not competitions:
            continue

          comp = competitions[0]
          competitors = comp.get("competitors", [])

          home_score, away_score = 0, 0
          home_name, away_name = "Local", "Visita"

          for team in competitors:
            if team.get("homeAway") == "home":
              home_name = team.get("team", {}).get("displayName", "Local")
              home_score = int(team.get("score", 0))
            else:
              away_name = team.get("team", {}).get("displayName", "Visita")
              away_score = int(team.get("score", 0))

          # Obtener nombre de la liga o torneo
          league = "Liga en Vivo"
          leagues_info = comp.get("league", {})
          if leagues_info:
            league = leagues_info.get("name", "Liga en Vivo")

          # Condición de alerta: Minuto 46 al 78 y marcador 0 - 0
          if 46 <= min_int <= 78 and (home_score + away_score) == 0:
            partidos_candidatos.append({
                "equipo_local": home_name,
                "equipo_visita": away_name,
                "minuto": min_int,
                "goles_local": home_score,
                "goles_visita": away_score,
                "liga": league,
            })
        except Exception:
          continue

      print(
          f"✅ Extraídos {len(partidos_candidatos)} partidos de Fútbol desde"
          " ESPN.",
          flush=True,
      )
    else:
      print(f"⚠️ Status code ESPN: {response.status_code}", flush=True)

  except Exception as e:
      print(f"⚠️ Error en consulta de ESPN: {e}", flush=True)

  return partidos_candidatos


# ==========================================
# 🏀 BALONCESTO PAUSADO
# ==========================================
async def extraer_basket_en_vivo():
  return []
  return []
