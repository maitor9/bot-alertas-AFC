import re
import requests


# ==========================================
# ⚽ SCRAPER HÍBRIDO (RADAR GLOBAL: 0-0 EN JUEGO + DESCANSO)
# ==========================================
async def extraer_futbol_en_vivo():
  partidos_candidatos = []
  print("⏳ Consultando API de ESPN (En juego y Descanso 0-0)...", flush=True)

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

          # Aceptamos partidos en juego ("in") o en descanso (estado "halftime" o "pre" / descripciones de descanso)
          status_desc = status.get("type", {}).get("description", "").lower()
          is_halftime = "half" in status_desc or "descanso" in status_desc or state == "halftime"

          if state != "in" and not is_halftime:
            continue

          # Extraer el minuto actual
          display_clock = status.get("displayClock", "45")
          min_int = 45
          match_min = re.search(r"\d+", str(display_clock))
          if match_min:
            min_int = int(match_min.group())

          # Si está en descanso pero la API dice 0 o 45, lo fijamos en 45 (HT)
          if is_halftime:
            min_int = 45

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

          # Reglas: 
          # 1. Partidos en segundo tiempo entre min 46 y 78 con 0-0
          # 2. O partidos en descanso (HT) con marcador 0-0
          condicion_segundo_tiempo = (46 <= min_int <= 78) and ((home_score + away_score) == 0)
          condicion_descanso = is_halftime and ((home_score + away_score) == 0)

          if condicion_segundo_tiempo or condicion_descanso:
            # Etiquetar minuto visual si está en descanso
            minuto_mostrar = "HT (Descanso)" if is_halftime else f"{min_int}'"

            # Filtro VIP por estadísticas (si aplica)
            es_vip = (total_remates >= 8) or (total_remates_puerta >= 4)

            partidos_candidatos.append({
                "equipo_local": home_name,
                "equipo_visita": away_name,
                "minuto": minuto_mostrar,
                "minuto_num": min_int, # Para orden interno si se requiere
                "goles_local": home_score,
                "goles_visita": away_score,
                "liga": league,
                "remates": total_remates,
                "remates_puerta": total_remates_puerta,
                "presion": equipo_mas_activo,
                "tipo": "VIP" if es_vip else "GLOBAL",
                "es_descanso": is_halftime
            })
        except Exception:
          continue

      print(
          f"✅ Extraídos {len(partidos_candidatos)} partidos para Radar Global (Juego y Descanso).",
          flush=True,
      )
    else:
      print(f"⚠️ Status code ESPN: {response.status_code}", flush=True)

  except Exception as e:
    print(f"⚠️ Error en consulta de ESPN: {e}", flush=True)

  return partidos_candidatos


async def extraer_basket_en_vivo():
  return []
