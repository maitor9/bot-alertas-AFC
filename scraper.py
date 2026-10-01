import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        " (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
}


# ==========================================
# ⚽ SCRAPER DE FÚTBOL EN VIVO (SOFASCORE LIVE API)
# ==========================================
async def extraer_futbol_en_vivo():
  partidos_candidatos = []
  print("⏳ Consultando Sofascore Fútbol en vivo...", flush=True)

  try:
    url = "https://api.sofascore.com/api/v1/sport/football/events/live"
    response = requests.get(url, headers=HEADERS, timeout=10)

    if response.status_code == 200:
      data = response.json()
      events = data.get("events", [])

      for event in events:
        try:
          # Filtro de minuto y estado del partido
          status = event.get("status", {})
          code = status.get("code")  # 6 = 1st half, 31 = HT, 7 = 2nd half

          # Solo buscamos en 2da mitad (code 7) o entretiempo
          if code != 7:
            continue

          # Minuto actual estimado o tiempo transcurrido
          time_info = event.get("time", {})
          minuto = time_info.get("played", 50)  # Minuto transcurrido por defecto

          # Marcador
          home_score = event.get("homeScore", {}).get("current", 0)
          away_score = event.get("awayScore", {}).get("current", 0)

          # Condición de alerta: 2da mitad (minuto 46 a 78) y va 0 - 0
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
      print(f"⚠️ Status code Sofascore: {response.status_code}", flush=True)

  except Exception as e:
    print(f"⚠️ Error en consulta de Sofascore: {e}", flush=True)

  return partidos_candidatos


# ==========================================
# 🏀 BALONCESTO PAUSADO TEMPORALMENTE
# ==========================================
async def extraer_basket_en_vivo():
  # Módulo en pausa para liberar 100% recursos
  return []
