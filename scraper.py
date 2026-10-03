import requests

SPORTMONKS_TOKEN = "jdLnSnODSlsqNmvFuMVppxOzhStnsD5MAvMJwQaPPNl82cejqS6bXTjQLnVt"


# ==========================================
# ⚽ SCRAPER SPORTMONKS (ESTRICTO CON xG >= 0.80)
# ==========================================
async def extraer_futbol_en_vivo():
  partidos_candidatos = []
  print("⏳ Consultando Sportmonks (Filtro con xG, Remates y Tiempo)...", flush=True)

  try:
    # URL de Sportmonks v3 con inclusión de estadísticas, marcadores, participantes y liga
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

          # REGLA DE TIEMPO: Minuto 46 al 80
          if not (46 <= min_int <= 80):
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
          total_remates = 0
          total_remates_puerta = 0
          total_xg = 0.0

          for stat in statistics:
            stat_type = str(stat.get("type_id", "")).lower()
            s_name = str(stat.get("name", "")).lower()

            h_val_raw = stat.get("home", 0) or 0
            a_val_raw = stat.get("away", 0) or 0

            # Identificar remates totales, remates a puerta y xG
            if "total shots" in s_name or "shots-total" in stat_type or stat.get("type_id") == 42:
              total_remates = int(h_val_raw) + int(a_val_raw)
            elif "shots on target" in s_name or "shots-on-target" in stat_type or stat.get("type_id") == 86:
              total_remates_puerta = int(h_val_raw) + int(a_val_raw)
            elif "expected_goals" in s_name or "expected goals" in s_name or "xg" in stat_type or stat.get("type_id") in [343, 594]: 
              # IDs comunes o nombres para xG en Sportmonks
              try:
                total_xg = float(h_val_raw) + float(a_val_raw)
              except:
                pass

          equipo_mas_activo = home_name

          # REGLAS ESTRICTAS: Remates >= 8 Y A puerta >= 4 Y xG >= 0.80
          condicion_remates = (total_remates >= 8) and (total_remates_puerta >= 4)
          
          # Nota: Si por alguna razón la liga del plan gratuito no expone xG (devuelve 0.0), 
          # puedes relajar temporalmente el xG o dejarlo condicionado. Aquí exigimos xG >= 0.80 si está presente, 
          # o puedes ajustarlo según veas el comportamiento en los logs.
          condicion_xg = total_xg >= 0.80

          if not (condicion_remates and condicion_xg):
            continue

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

      print(f"✅ Extraídos {len(partidos_candidatos)} partidos con filtro xG.", flush=True)
    else:
      print(f"⚠️ Status code Sportmonks: {response.status_code}", flush=True)

  except Exception as e:
    print(f"⚠️ Error consultando Sportmonks: {e}", flush=True)

  return partidos_candidatos


async def extraer_basket_en_vivo():
  return []
