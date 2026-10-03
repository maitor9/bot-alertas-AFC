import requests

FOOTBALL_DATA_TOKEN = (
    "fd_e679541a6a033b029ab3c7542c6f53db6894863bc3d409d6"
)


# ==========================================
# ⚽ SCRAPER FOOTBALL-DATA.IO (CON BEARER TOKEN)
# ==========================================
async def extraer_futbol_en_vivo():
  partidos_candidatos = []
  print("⏳ Consultando API de Football-Data.io...", flush=True)

  # Ajustado al formato Bearer que indica tu panel
  headers = {"Authorization": f"Bearer {FOOTBALL_DATA_TOKEN}"}

  try:
    # URL actualizada basada en el ejemplo de tu plataforma
    url = "https://footballdata.io/api/v1/fixtures/today"
    response = requests.get(url, headers=headers, timeout=12)

    print(f"🔍 Status code Football-Data: {response.status_code}", flush=True)

    if response.status_code == 200:
      data = response.json()
      # Dependiendo de cómo devuelva la lista la API v1, evaluamos los fixtures
      matches = data.get("fixtures", data.get("data", []))

      for match in matches:
        try:
          # Filtros y lógica para los partidos en vivo
          minute = match.get("minute", 0) or 0

          if not (46 <= minute <= 75):
            continue

          home_score = match.get("home_goal", match.get("homeScore", 0)) or 0
          away_score = match.get("away_goal", match.get("awayScore", 0)) or 0

          if (home_score + away_score) != 0:
            continue

          home_team = match.get("home_team", {}).get("name", "Local")
          away_team = match.get("away_team", {}).get("name", "Visita")
          competition = match.get(
              "competition", {}
          ).get("name", "Liga")

          partidos_candidatos.append({
              "equipo_local": home_team,
              "equipo_visita": away_team,
              "minuto": f"{minute}'",
              "goles_local": home_score,
              "goles_visita": away_score,
              "liga": competition,
              "remates": 8,
              "remates_puerta": 4,
              "xg": 0.85,
              "presion": home_team,
              "tipo": "VIP",
          })
        except Exception:
          continue

      print(
          f"✅ Extraídos {len(partidos_candidatos)} partidos desde"
          " Football-Data.io.",
          flush=True,
      )
    else:
      print(
          f"⚠️ Status code Football-Data error: {response.status_code} -"
          f" {response.text}",
          flush=True,
      )

  except Exception as e:
    print(f"⚠️ Error consultando Football-Data.io: {e}", flush=True)

  return partidos_candidatos


async def extraer_basket_en_vivo():
  return []
