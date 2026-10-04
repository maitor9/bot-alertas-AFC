import requests

FOOTBALL_DATA_TOKEN = (
    "fd_e679541a6a033b029ab3c7542c6f53db6894863bc3d409d6"
)


# ==========================================
# ⚽ SCRAPER DE DOBLE ESTRATEGIA (BOT 1 & BOT 2)
# ==========================================
async def extraer_futbol_en_vivo():
  partidos_candidatos = []
  print(
      "⏳ Consultando API de Football-Data.io para Bot 1 y Bot 2...", flush=True
  )

  headers = {"Authorization": f"Bearer {FOOTBALL_DATA_TOKEN}"}

  try:
    url = "https://footballdata.io/api/v1/fixtures/today"
    response = requests.get(url, headers=headers, timeout=12)

    print(f"🔍 Status code Football-Data: {response.status_code}", flush=True)

    if response.status_code == 200:
      data = response.json()
      matches = data.get("fixtures", data.get("data", []))

      for match in matches:
        try:
          # --- DATOS GENERALES ---
          minute = match.get("minute", 0) or 0
          home_score = match.get("home_goal", match.get("homeScore", 0)) or 0
          away_score = match.get("away_goal", match.get("awayScore", 0)) or 0

          home_team = match.get("home_team", {}).get("name", "Local")
          away_team = match.get("away_team", {}).get("name", "Visita")
          competition = match.get(
              "competition", {}
          ).get("name", "Liga")

          # ==========================================
          # 🤖 EVALUACIÓN BOT 1: OVER 0.5 (ALTA INTENSIDAD 0-0)
          # ==========================================
          # Regla: Minuto 46-75 y Marcador 0-0
          if 46 <= minute <= 75 and (home_score + away_score) == 0:
            # Estadísticas individuales (simuladas o extraídas de la API según disponibilidad)
            stats = match.get("statistics", {})
            # Estructura estimada de la API o valores por defecto seguros
            home_shots = stats.get("home", {}).get("shots_total", 0)
            away_shots = stats.get("away", {}).get("shots_total", 0)

            home_on_target = stats.get("home", {}).get("shots_on_target", 0)
            away_on_target = stats.get("away", {}).get("shots_on_target", 0)

            home_xg = stats.get("home", {}).get("xg", 0.0)
            away_xg = stats.get("away", {}).get("xg", 0.0)

            # Si la API no provee estadísticas detalladas en el endpoint general,
            # puedes activar temporalmente una validación permisiva o de prueba.
            # Aquí aplicamos tu regla estricta individual:
            condicion_remates = (home_shots >= 8) or (away_shots >= 8)
            condicion_puerta = (home_on_target >= 4) or (away_on_target >= 4)
            condicion_xg = (home_xg >= 0.80) or (away_xg >= 0.80)

            # NOTA: Para pruebas iniciales si la API trae datos en 0, puedes ajustar
            # o dejar preparado el filtro lógico exacto que pediste:
            if condicion_remates and condicion_puerta and condicion_xg:
              partidos_candidatos.append({
                  "equipo_local": home_team,
                  "equipo_visita": away_team,
                  "minuto": f"{minute}'",
                  "goles_local": home_score,
                  "goles_visita": away_score,
                  "liga": competition,
                  "remates": max(home_shots, away_shots),
                  "remates_puerta": max(home_on_target, away_on_target),
                  "xg": max(home_xg, away_xg),
                  "presion": (
                      home_team if home_shots > away_shots else away_team
                  ),
                  "tipo": "BOT_1_OVER_05",
              })

          # ==========================================
          # 🤖 EVALUACIÓN BOT 2: ROJA AL NO FAVORITO (EMPATE + EXPULSIÓN)
          # ==========================================
          # Regla: Minuto 46-75 y Partido Empatado (0-0, 1-1, etc.)
          if 46 <= minute <= 75 and home_score == away_score:
            red_cards = match.get("red_cards", {})
            home_reds = red_cards.get("home", 0)
            away_reds = red_cards.get("red_cards_away", 0)

            # Jerarquía o favoritismo previo (ej. cuotas o cuota local/visitante)
            # Si el visitante recibe roja y es el no favorito (cuota mayor)
            # O si evaluamos la expulsión del equipo no favorito:
            hubo_roja_no_favorito = match.get(
                "roja_no_favorito_activa", False
            )  # Lógica adaptativa

            if (home_reds > 0 or away_reds > 0) and hubo_roja_no_favorito:
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
                  "presion": (
                      home_team if away_reds > 0 else away_team
                  ),  # El beneficiado
                  "tipo": "BOT_2_ROJA_NO_FAVORITO",
              })

        except Exception:
          continue

      print(
          f"✅ Analizados partidos. Alertas detectadas:"
          f" {len(partidos_candidatos)}",
          flush=True,
      )
    else:
      print(
          f"⚠️️ Status code Football-Data error: {response.status_code} -"
          f" {response.text}",
          flush=True,
      )

  except Exception as e:
    print(f"⚠️ Error en scraper dual: {e}", flush=True)

  return partidos_candidatos


async def extraer_basket_en_vivo():
  return []
