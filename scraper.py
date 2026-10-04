import requests

FOOTBALL_DATA_TOKEN = (
    "fd_e679541a6a033b029ab3c7542c6f53db6894863bc3d409d6"
)


# ==========================================
# ⚽ SCRAPER FOOTBALLDATA.IO (DOMINIO .IO Y BEARER)
# ==========================================
async def extraer_futbol_en_vivo():
  partidos_candidatos = []
  print("⏳ Consultando API de Footballdata.io...", flush=True)

  # Formato exacto que exige tu panel con Bearer
  headers = {"Authorization": f"Bearer {FOOTBALL_DATA_TOKEN}"}

  try:
    # URL oficial de la plataforma .io según tu panel
    url = "https://footballdata.io/api/v1/fixtures/today"
    response = requests.get(url, headers=headers, timeout=12)

    print(f"🔍 Status code Footballdata.io: {response.status_code}", flush=True)

    if response.status_code == 200:
      data = response.json()
      matches = data.get("fixtures", data.get("data", []))

      for match in matches:
        try:
          minute = match.get("minute", 0) or 0
          home_score = match.get("home_goal", match.get("homeScore", 0)) or 0
          away_score = match.get("away_goal", match.get("awayScore", 0)) or 0

          home_team = match.get("home_team", {}).get("name", "Local")
          away_team = match.get("away_team", {}).get("name", "Visita")
          competition = match.get(
              "competition", {}
          ).get("name", "Liga")

          # ==========================================
          # 🤖 BOT 1: OVER 0.5 (Min 46-75, 0-0, Individuales >=8, >=4, >=0.80)
          # ==========================================
          if 46 <= minute <= 75 and (home_score + away_score) == 0:
            stats = match.get("statistics", {})
            home_shots = stats.get("home", {}).get("shots_total", 0)
            away_shots = stats.get("away", {}).get("shots_total", 0)

            home_on_target = stats.get("home", {}).get("shots_on_target", 0)
            away_on_target = stats.get("away", {}).get("shots_on_target", 0)

            home_xg = stats.get("home", {}).get("xg", 0.0)
            away_xg = stats.get("away", {}).get("xg", 0.0)

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
          # 🤖 BOT 2: ROJA AL NO FAVORITO (Empate + Roja)
          # ==========================================
          if 46 <= minute <= 75 and home_score == away_score:
            red_cards = match.get("red_cards", {})
            home_reds = red_cards.get("home", 0)
            away_reds = red_cards.get("away", 0)
            roja_no_favorito = match.get("roja_no_favorito_activa", False)

            if (home_reds > 0 or away_reds > 0) and roja_no_favorito:
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
                  ),
                  "tipo": "BOT_2_ROJA_NO_FAVORITO",
              })

        except Exception:
          continue

      print(
          f"✅ Analizados partidos con Footballdata.io. Alertas detectadas:"
          f" {len(partidos_candidatos)}",
          flush=True,
      )
    else:
      print(
          f"⚠️ Status code Footballdata.io error: {response.status_code} -"
          f" {response.text}",
          flush=True,
      )

  except Exception as e:
    print(f"⚠️ Error consultando Footballdata.io: {e}", flush=True)

  return partidos_candidatos


async def extraer_basket_en_vivo():
  return []
