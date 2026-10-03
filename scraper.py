import requests

SPORTMONKS_TOKEN = "jdLnSnODSlsqNmvFuMVppxOzhStnsD5MAvMJwQaPPNl82cejqS6bXTjQLnVt"


# ==========================================
# ⚽ SCRAPER SPORTMONKS (ESTRICTO: MIN 46-80, 0-0, REMATES >=8 Y A PUERTA >=4)
# ==========================================
async def extraer_futbol_en_vivo():
  partidos_candidatos = []
  print("⏳ Consultando API en vivo de Sportmonks (v3)...", flush=True)

  try:
    # URL oficial de Sportmonks v3 con inclusión de estadísticas, marcadores, participantes y liga
    url = f"https://api.sportmonks.com/v3/football/livescores/inplay?api_token={SPORTMONKS_TOKEN}&include=participants;scores;statistics;league"
    response = requests.get(url, timeout=12)

    print(
        f"🔍 Status code Sportmonks Live: {response.status_code}", flush=True
    )

    if response.status_code == 200:
      data = response.json()
      matches = data.get("data", [])

      for match in matches:
        try:
          # Verificar que esté en juego (LIVE)
          status_info = match.get("status", "")
          if status_info != "LIVE":
            continue

          # Minuto actual del partido
          time_data = match.get("time", {})
          min_int = time_data.get("minute", 0)

          # REGLA DE TIEMPO: Estrictamente entre el minuto 46 y el 80
          if not (46 <= min_int <= 80):
            continue

          # Equipos participantes
          participants = match.get("participants", [])
          home_name, away_name = "Local", "Visita"

          for p in participants:
            meta = p.get("meta", {})
            if meta.get("location") == "home":
              home_name = p.get("name", "Local")
            elif meta.get("location") == "away":
              away_name = p.get("name", "Visita")

          # Marcadores actuales (buscamos 0-0)
          scores = match.get("scores", [])
          home_score, away_score = 0, 0
          for score in scores:
            if score.get("description") == "CURRENT":
              s_loc = score.get("score", {}).get("participant", "")
              if s_loc == "home":
                home_score = score.get("score", {}).get("goals", 0)
              elif s_loc == "away":
                away_score = score.get("score", {}).get("goals", 0)

          # REGLA 1: Total de goles igual a 0
          if (home_score + away_score) != 0:
            continue

          # Nombre de la liga
          league_info = match.get("league", {})
          league_name = league_info.get("name", "Liga en Vivo")

          # Estadísticas en vivo de Sportmonks
          statistics = match.get("statistics", [])
          total_remates = 0
          total_remates_puerta = 0

          for stat in statistics:
            stat_type = str(stat.get("type_id", "")).lower()
            s_name = str(stat.get("name", "")).lower()

            h_val = int(stat.get("home", 0) or 0)
            a_val = int(stat.get("away", 0) or 0)

            # Identificar remates totales y a puerta según Sportmonks v3
            if (
                "total shots" in s_name
                or "shots-total" in stat_type
                or stat.get("type_id") == 42
            ):
              total_remates = h_val + a_val
            elif (
                "shots on target" in s_name
                or "shots-on-target" in stat_type
                or stat.get("type_id") == 86
            ):
              total_remates_puerta = h_val + a_val

          equipo_mas_activo = home_name

          # REGLA 2 & 3 (ESTRICTO CON Y / AND): Remates totales >= 8 Y Remates a puerta >= 4
          condicion_remates_estricta = (total_remates >= 8) and (
              total_remates_puerta >= 4
          )
          if not condicion_remates_estricta:
            continue

          # Si pasa todo, se añade como partido VIP elegible
          partidos_candidatos.append({
              "equipo_local": home_name,
              "equipo_visita": away_name,
              "minuto": f"{min_int}'",
              "goles_local": home_score,
              "goles_visita": away_score,
              "liga": league_name,
              "remates": total_remates,
              "remates_puerta": total_remates_puerta,
              "presion": equipo_mas_activo,
              "tipo": "VIP",
          })
        except Exception:
          continue

      print(
          f"✅ Extraídos {len(partidos_candidatos)} partidos estrictos desde"
          " Sportmonks.",
          flush=True,
      )
    else:
      print(f"⚠️ Status code Sportmonks: {response.status_code}", flush=True)

  except Exception as e:
    print(f"⚠️ Error consultando Sportmonks: {e}", flush=True)

  return partidos_candidatos


async def extraer_basket_en_vivo():
  return []
