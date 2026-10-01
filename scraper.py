import re
import requests


# ==========================================
# ⚽ SCRAPER HÍBRIDO (ESPN API: GLOBAL + VIP)
# ==========================================
async def extraer_futbol_en_vivo():
  partidos_candidatos = []
  print("⏳ Consultando API pública de ESPN (Radar Global y VIP)...", flush=True)

  try:
    url = "https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard"
    response = requests.get(url, timeout=12)

    if response.status_code == 200:
      data = response.json()
      events = data.get("events", [])

      for event in events:
        try:
          status = event.get("status", {})
          state = status.get("type", {}).get("state", "")

          # Solo partidos en juego ("in")
          if state != "in":
            continue

          # Extraer el minuto actual
          display_clock = status.get("displayClock", "50")
          min_int = 50
          match_min = re.search(r"\d+", str(display_clock))
          if match_min:
            min_int = int(match_min.group())

          competitions = event.get("competitions", [])
          if not competitions:
            continue

          comp = competitions[0]
          competitors = comp.get("competitors", [])

          home_score, away_score = 0, 0
          home_name, away_name = "Local", "Visita"
          home_shots, away_shots = 0, 0
          home_sot, away_sot = 0, 0

          for team in competitors:
            is_home = team.get("homeAway") == "home"
            name = team.get("team", {}).get("displayName", "Equipo")
            score = int(team.get("score", 0))

            total_s = 0
            on_target_s = 0
            statistics = team.get("statistics", [])
            for stat in statistics:
              s_name = stat.get("name", "").lower()
              s_val = stat.get("value", 0)
              if "shotstotal" in s_name or s_name == "shots":
                total_s = int(s_val)
              elif "shotsontarget" in s_name:
                on_target_s = int(s_val)

            if is_home:
              home_name = name
              home_score = score
              home_shots = total_s
              home_sot = on_target_s
            else:
              away_name = name
              away_score = score
              away_shots = total_s
              away_sot = on_target_s

          total_remates = home_shots + away_shots
          total_remates_puerta = home_sot + away_sot
          equipo_mas_activo = home_name if home_shots >= away_shots else away_name

          league = "Liga en Vivo"
          leagues_info = comp.get("league", {})
          if leagues_info:
            league = leagues_info.get("name", "Liga en Vivo")

          # Regla base estricta: Minuto 46 a 78 y marcador 0 - 0
          condicion_minuto = 46 <= min_int <= 78
          condicion_goles = (home_score + away_score) == 0

          if condicion_minuto and condicion_goles:
            # Filtro VIP: si la API provee estadísticas y cumplen con el umbral
            es_vip = (total_remates >= 8) or (total_remates_puerta >= 4)

            partidos_candidatos.append({
                "equipo_local": home_name,
                "equipo_visita": away_name,
                "minuto": min_int,
                "goles_local": home_score,
                "goles_visita": away_score,
                "liga": league,
                "remates": total_remates,
                "remates_puerta": total_remates_puerta,
                "presion": equipo_mas_activo,
                "tipo": "VIP" if es_vip else "GLOBAL",
            })
        except Exception:
          continue

      print(
          f"✅ Extraídos {len(partidos_candidatos)} partidos totales desde ESPN.",
          flush=True,
      )
    else:
      print(f"⚠️ Status code ESPN: {response.status_code}", flush=True)

  except Exception as e:
    print(f"⚠️ Error en consulta de ESPN: {e}", flush=True)

  return partidos_candidatos


# ==========================================
# 🏀 BALONCESTO PAUSADO
# ==========================================
async def extraer_basket_en_vivo():
  return []
