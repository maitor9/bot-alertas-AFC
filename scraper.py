import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        " (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Referer": "https://www.sofascore.com/",
    "Origin": "https://www.sofascore.com",
    "Sec-Ch-Ua": (
        '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"'
    ),
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
}


# ==========================================
# ⚽ SCRAPER DE FÚTBOL EN VIVO (SOFASCORE API)
# ==========================================
async def extraer_futbol_en_vivo():
  partidos_candidatos = []
  print("⏳ Consultando Sofascore Fútbol en vivo...", flush=True)

  try:
    url = "https://api.sofascore.com/api/v1/sport/football/events/live"
    response = requests.get(url, headers=HEADERS, timeout=12)

    print(f"🔍 Status code recibido de Sofascore: {response.status_code}", flush=True)

    if response.status_code == 200:
      data = response.json()
      events = data.get("events", [])

      for event in events:
        try:
          status = event.get("status", {})
          code = status.get("code")  # 7 = 2da mitad

          if code != 7:
            continue

          time_info = event.get("time", {})
          minuto = time_info.get("played", 50)

          home_score = event.get("homeScore", {}).get("current", 0)
          away_score = event.get("awayScore", {}).get("current", 0)

          if 46 <= minuto <= 78 and (home_score + away_score) == 0:
            local = event.get("homeTeam", {}).get("name", "Local")
            visita = event.get("awayTeam", {}).get("name", "Visita")
            liga = event.get("tournament", {}).get("name", "Liga")

            partidos_candidatos.append({
                "equipo_local": local,
                "equipo_visita": visita,
                "minuto": minuto,
                "goles_local": home_score,
                "goles_visita": away_score,
                "liga": liga,
            })
        except Exception:
          continue

      print(
          f"✅ Extraídos {len(partidos_candidatos)} partidos de Fútbol de"
          " Sofascore.",
          flush=True,
      )
    else:
      print(f"⚠️ Sofascore denegó el acceso (Status: {response.status_code})", flush=True)

  except Exception as e:
    print(f"⚠️️ Error en consulta de Sofascore: {e}", flush=True)

  return partidos_candidatos


# ==========================================
# 🏀 BALONCESTO PAUSADO
# ==========================================
async def extraer_basket_en_vivo():
  return []
