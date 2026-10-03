import requests

FOOTBALL_DATA_TOKEN = (
    "fd_e679541a6a033b029ab3c7542c6f53db6894863bc3d409d6"
)


# ==========================================
# ⚽ SCRAPER FOOTBALL-DATA.ORG
# ==========================================
async def extraer_futbol_en_vivo():
  partidos_candidatos = []
  print("⏳ Consultando API de Football-Data.org...", flush=True)

  headers = {"X-Auth-Token": FOOTBALL_DATA_TOKEN}

  try:
    url = "https://api.football-data.org/v4/matches?status=LIVE"
    response = requests.get(url, headers=headers, timeout=12)

    print(f"🔍 Status code Football-Data: {response.status_code}", flush=True)

    if response.status_code == 200:
      data = response.json()
      matches = data.get("matches", [])

      for match in matches:
        try:
          # Minuto del partido
          minute = match.get("minute", 0) or 0

          # REGLA DE TIEMPO: Minuto 46 al 75
          if not (46 <= minute <= 75):
            continue

          score = match.get("score", {})
          # Marcador actual en el tiempo reglamentario (regular time)
          regular_time = score.get("regularTime", {})
          home_score = regular_time.get("home", 0) or 0
          away_score = regular_time.get("away", 0) or 0

          # Si no viene en regularTime, intentamos con score['fullTime'] o current
          if home_score is None:
            home_score = 0
          if away_score is None:
            away_score = 0

          # REGLA 1: Total de goles igual a 0
          if (home_score + away_score) != 0:
            continue

          home_team = match.get("homeTeam", {}).get("name", "Local")
          away_team = match.get("awayTeam", {}).get("name", "Visita")
          competition = match.get("competition", {}).get("name", "Liga")

          # Football-data.org en su plan gratuito de lista en vivo no siempre expone
          # remates ni xG directamente aquí. Dejaremos valores base y evaluaremos
          # el comportamiento según los partidos que devuelva la API.
          total_remates = 8  # Placeholder para validación inicial
          total_remates_puerta = 4
          xg_equipo = 0.85

          partidos_candidatos.append({
              "equipo_local": home_team,
              "equipo_visita": away_team,
              "minuto": f"{minute}'",
              "goles_local": home_score,
              "goles_visita": away_score,
              "liga": competition,
              "remates": total_remates,
              "remates_puerta": total_remates_puerta,
              "xg": xg_equipo,
              "presion": home_team,
              "tipo": "VIP",
          })
        except Exception:
          continue

      print(
          f"✅ Extraídos {len(partidos_candidatos)} partidos desde"
          " Football-Data.",
          flush=True,
      )
    else:
      print(
          f"⚠️ Status code Football-Data error: {response.status_code} -"
          f" {response.text}",
          flush=True,
      )

  except Exception as e:
    print(f"⚠️️ Error consultando Football-Data: {e}", flush=True)

  return partidos_candidatos


async def extraer_basket_en_vivo():
  return []
