import requests

SPORTMONKS_TOKEN = "jdLnSnODSlsqNmvFuMVppxOzhStnsD5MAvMJwQaPPNl82cejqS6bXTjQLnVt"


# ==========================================
# ⚽ SCRAPER SPORTMONKS (MIN 46-75, 0-0, REMATES Y xG INDIVIDUAL >= 0.80)
# ==========================================
async def extraer_futbol_en_vivo():
  partidos_candidatos = []
  print("⏳ Consultando Sportmonks (Filtro Min 46-75 + xG Individual)...", flush=True)

  try:
    url = f"https://api.sportmonks.com/v3/football/livescores/inplay?api_token={SPORTMONKS_TOKEN}&include=participants;scores;statistics;league"
    response = requests.get(url, timeout=12)

    if response.status_code == 200:
      data = response.json()
      matches = data.get("data", [])

      for match in matches:
        try:
          status_info = match.get("status", "")
          if status_info != "LIVE":
            continue

          time_data = match.get("time", {})
          min_int = time_data.get("minute", 0)

          # REGLA DE TIEMPO: Estrictamente entre el minuto 46 y el 75
          if not (46 <= min_int <= 75):
            continue

          participants = match.get("participants", [])
          home_name, away_name = "Local", "Visita"

          for p in participants:
            meta = p.get("meta", {})
            if meta.get("location") == "home":
              home_name = p.get("name", "Local")
            elif meta.get("location") == "away":
              away_name = p.get("name", "Visita")

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

          league_info = match.get("league", {})
          league_name = league_info.get("name", "Liga en Vivo")

          statistics = match.get("statistics", [])
          home_remates, away_remates = 0, 0
          home_puerta, away_puerta = 0, 0
          home_xg, away_xg = 0.0, 0.0

          for stat in statistics:
            stat_type = str(stat.get("type_id", "")).lower()
            s_name = str(stat.get("name", "")).lower()

            try:
              h_val = float(stat.get("home", 0) or 0)
              a_val = float(stat.get("away", 0) or 0)
            except:
              h_val, a_val = 0.0, 0.0

            # Capturar estadísticas separadas por equipo
            if "total shots" in s_name or "shots-total" in stat_type or stat.get("type_id") == 42:
              home_remates = int(h_val)
              away_remates = int(a_val)
            elif "shots on target" in s_name or "shots-on-target" in stat_type or stat.get("type_id") == 86:
              home_puerta = int(h_val)
              away_puerta = int(a_val)
            elif "expected_goals" in s_name or "expected goals" in s_name or "xg" in stat_type or stat.get("type_id") in [343, 594]:
              home_xg = h_val
              away_xg = a_val

          total_remates = home_remates + away_remates
          total_remates_puerta = home_puerta + away_puerta
          total_xg = home_xg + away_xg

          # REGLA 2: Remates totales del partido >= 8 Y Remates a puerta >= 4
          condicion_remates = (total_remates >= 8) and (total_remates_puerta >= 4)

          # REGLA 3: Al menos uno de los dos equipos debe tener un xG individual >= 0.80
          condicion_xg_individual = (home_xg >= 0.80) or (away_xg >= 0.80)

          if not (condicion_remates and condicion_xg_individual):
            continue

          equipo_mas_activo = home_name if home_xg >= away_xg else away_name

          partidos_candidatos.append({
              "equipo_local": home_name,
              "equipo_visita": away_name,
              "minuto": f"{min_int}'",
              "goles_local": home_score,
              "goles_visita": away_score,
              "liga": league_name,
              "remates": total_remates,
              "remates_puerta": total_remates_puerta,
              "xg": round(total_xg, 2),
              "presion": equipo_mas_activo,
              "tipo": "VIP",
          })
        except Exception:
          continue

      print(f"✅ Extraídos {len(partidos_candidatos)} partidos cumpliendo xG individual y rango 46-75.", flush=True)
    else:
      print(f"⚠️ Status code Sportmonks: {response.status_code}", flush=True)

  except Exception as e:
    print(f"⚠️ Error consultando Sportmonks: {e}", flush=True)

  return partidos_candidatos


async def extraer_basket_en_vivo():
  return []
