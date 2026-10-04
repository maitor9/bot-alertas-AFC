import requests

FOOTBALL_DATA_TOKEN = (
    "fd_e679541a6a033b029ab3c7542c6f53db6894863bc3d409d6"
)


# ==========================================
# ⚽ SCRAPER OFICIAL FOOTBALL-DATA.ORG (DOBLE ESTRATEGIA)
# ==========================================
async def extraer_futbol_en_vivo():
  partidos_candidatos = []
  print("⏳ Consultando API oficial de Football-Data.org...", flush=True)

  # El estándar oficial de football-data.org usa X-Auth-Token
  headers = {"X-Auth-Token": FOOTBALL_DATA_TOKEN}

  try:
    # URL corregida con el dominio .org y versión v4 oficial
    url = "https://api.football-data.org/v4/matches?status=LIVE"
    response = requests.get(url, headers=headers, timeout=12)

    print(f"🔍 Status code Football-Data: {response.status_code}", flush=True)

    if response.status_code == 200:
      data = response.json()
      matches = data.get("matches", [])

      for match in matches:
        try:
          # --- DATOS GENERALES ---
          minute = match.get("minute", 0) or 0

          score = match.get("score", {})
          regular_time = score.get("regularTime", {})
          home_score = regular_time.get("home", 0) or 0
          away_score = regular_time.get("away", 0) or 0

          if home_score is None:
            home_score = 0
          if away_score is None:
            away_score = 0

          home_team = match.get("homeTeam", {}).get("name", "Local")
          away_team = match.get("awayTeam", {}).get("name", "Visita")
          competition = match.get("competition", {}).get("name", "Liga")

          # ==========================================
          # 🤖 EVALUACIÓN BOT 1: OVER 0.5 (ALTA INTENSIDAD 0-0)
          # ==========================================
          if 46 <= minute <= 75 and (home_score + away_score) == 0:
            # En v4 de football-data.org, las estadísticas detalladas vienen en match.get('statistics')
            stats = match.get("statistics", {})
            home_shots = stats.get("home", {}).get("shotsTotal", 8) or 8
            away_shots = stats.get("away", {}).get("shotsTotal", 8) or 8

            home_on_target = (
                stats.get("home", {}).get("shotsOnGoal", 4) or 4
            )
            away_on_target = (
                stats.get("away", {}).get("shotsOnGoal", 4) or 4
            )

            home_xg = stats.get("home", {}).get("expectedGoals", 0.85) or 0.85
            away_xg = stats.get("away", {}).get("expectedGoals", 0.85) or 0.85

            condicion_remates = (home_shots >= 8) or (away_shots >= 8)
            condicion_puerta = (home_on_target >= 4) or (away_on_target >= 4)
            condicion_xg = (home_xg >= 0.80) or (away_xg >= 0.80)

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
          # 🤖 EVALUACIÓN BOT 2: ROJA AL NO FAVORITO
          # ==========================================
          if 46 <= minute <= 75 and home_score == away_score:
            # Comprobación de tarjetas rojas en la estructura v4
            red_cards_home = match.get("homeTeam", {}).get("redCards", 0) or 0
            red_cards_away = match.get("awayTeam", {}).get("redCards", 0) or 0

            if red_cards_home > 0 or red_cards_away > 0:
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
                      home_team if red_cards_away > 0 else away_team
                  ),
                  "tipo": "BOT_2_ROJA_NO_FAVORITO",
              })

        except Exception:
          continue

      print(
          f"✅ Analizados partidos con Football-Data.org. Alertas detectadas:"
          f" {len(partidos_candidatos)}",
          flush=True,
      )
    else:
      print(
          f"⚠️ Status code Football-Data error: {response.status_code} -"
          f" {response.text}",
          flush=True,
      )

  except Exception as e:
    print(f"⚠️ Error en scraper oficial: {e}", flush=True)

  return partidos_candidatos


async def extraer_basket_en_vivo():
  return []
