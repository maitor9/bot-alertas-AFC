import requests

FOOTBALL_DATA_TOKEN = (
    "fd_e679541a6a033b029ab3c7542c6f53db6894863bc3d409d6"
)


# ==========================================
# ⚽ SCRAPER MULTI-ESTRATEGIA (Football-Data.io)
# ==========================================
async def extraer_futbol_en_vivo():
  # Retornaremos una lista combinada o estructurada por tipos de alerta
  partidos_candidatos = []
  print("⏳ Consultando multi-estrategia en Football-Data.io...", flush=True)

  headers = {"Authorization": f"Bearer {FOOTBALL_DATA_TOKEN}"}

  try:
    url = "https://api.football-data.org/v4/matches?status=LIVE"
    response = requests.get(url, headers=headers, timeout=12)

    if response.status_code == 200:
      data = response.json()
      matches = data.get("matches", [])

      for match in matches:
        try:
          minute = match.get("minute", 0) or 0
          score = match.get("score", {})
          regular_time = score.get("regularTime", {})
          home_score = regular_time.get("home", 0) or 0
          away_score = regular_time.get("away", 0) or 0

          home_team = match.get("homeTeam", {}).get("name", "Local")
          away_team = match.get("awayTeam", {}).get("name", "Visita")
          competition = match.get("competition", {}).get("name", "Liga")

          # ==========================================
          # ESTRATEGIA 1: OVER 0.5 (Min 46-75, 0-0)
          # ==========================================
          if 46 <= minute <= 75 and (home_score + away_score) == 0:
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
                "tipo": "VIP_GOL",  # Etiqueta para estrategia de goles
                "mensaje_extra": "Estrategia Over 0.5 (Min 46-75, 0-0)",
            })

          # ==========================================
          # ESTRATEGIA 2: EMPATE + ROJA AL NO FAVORITO / VISITANTE
          # ==========================================
          # Validamos si van empatados
          if home_score == away_score:
            # Verificamos si hay estadísticas de tarjetas o incidencias en el partido
            # (Football-Data incluye bookings en algunos planes o podemos evaluar eventos)
            bookings = match.get("bookings", [])
            red_cards_away = 0

            for card in bookings:
              if (
                  card.get("participant", "") == "away"
                  and card.get("card") == "RED"
              ):
                red_cards_away += 1

            # Si el visitante (usualmente considerado no favorito de visita) recibe roja y van empatados
            if red_cards_away > 0:
              partidos_candidatos.append({
                  "equipo_local": home_team,
                  "equipo_visita": away_team,
                  "minuto": f"{minute}'",
                  "goles_local": home_score,
                  "goles_visita": away_score,
                  "liga": competition,
                  "remates": 0,
                  "remates_puerta": 0,
                  "xg": 0.0,
                  "presion": home_team,
                  "tipo": (
                      "ROJA_TACTICA"
                  ),  # Etiqueta para estrategia de expulsión
                  "mensaje_extra": (
                      "¡Empate y Roja al visitante! Oportunidad para el local."
                  ),
              })

        except Exception:
          continue

      print(
          f"✅ Extraídos {len(partidos_candidatos)} eventos totales bajo"
          " multi-estrategia.",
          flush=True,
      )
    else:
      print(
          f"⚠️ Error API Football-Data: {response.status_code} -"
          f" {response.text}",
          flush=True,
      )

  except Exception as e:
    print(f"⚠️ Error en scraper multi-estrategia: {e}", flush=True)

  return partidos_candidatos


async def extraer_basket_en_vivo():
  return []
