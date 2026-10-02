import re
import requests


# ==========================================
# ⚽ SCRAPER DE FÚTBOL PURIFICADO (EXCLUYE BASKETBALL Y OTROS)
# ==========================================
async def extraer_futbol_en_vivo():
  partidos_candidatos = []
  print(
      "⏳ Consultando API de ESPN (Filtrando estrictamente solo fútbol)...",
      flush=True,
  )

  try:
    url = "https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard"
    response = requests.get(url, timeout=12)

    if response.status_code == 200:
      data = response.json()
      events = data.get("events", [])

      for event in events:
        try:
          # Validar primero la liga y el nombre del torneo para descartar baloncesto u otros deportes colados
          competitions = event.get("competitions", [])
          if not competitions:
            continue

          comp = competitions[0]
          leagues_info = comp.get("league", {})
          league_name = (
              leagues_info.get("name", "Liga en Vivo")
              if leagues_info
              else "Liga en Vivo"
          )
          league_lower = league_name.lower()

          # Filtro de seguridad: Si la liga menciona baloncesto o basket, se descarta de inmediato
          if (
              "basketball" in league_lower
              or "baloncesto" in league_lower
              or "nba" in league_lower
              or "ncaa" in league_lower
          ):
            continue

          status = event.get("status", {})
          state = status.get("type", {}).get("state", "")

          status_desc = status.get("type", {}).get("description", "").lower()
          is_halftime = (
              "half" in status_desc
              or "descanso" in status_desc
              or state == "halftime"
          )

          if state != "in" and not is_halftime:
            continue

          display_clock = status.get("displayClock", "45")
          min_int = 45
          match_min = re.search(r"\d+", str(display_clock))
          if match_min:
            min_int = int(match_min.group())

          if is_halftime:
            min_int = 45

          competitors = comp.get("competitors", [])

          home_score, away_score = 0, 0
          home_name, away_name = "Local", "Visita"
          home_shots, away_shots = 0, 0
          home_sot, away_sot = 0, 0

          for team in competitors:
            is_home = team.get("homeAway") == "home"
            name = team.get("team", {}).get("displayName", "Equipo")

            raw_score = team.get("score", 0)
            score = int(raw_score) if str(raw_score).isdigit() else 0

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

          # --- VALIDACIÓN ESTRICTA DE 0-0 REAL EN FÚTBOL ---
          marcador_total = home_score + away_score
          if marcador_total != 0:
            continue

          condicion_segundo_tiempo = 46 <= min_int <= 78
          condicion_descanso = is_halftime

          if condicion_segundo_tiempo or condicion_descanso:
            minuto_mostrar = "HT (Descanso)" if is_halftime else f"{min_int}'"
            es_vip = (total_remates >= 8) or (total_remates_puerta >= 4)

            partidos_candidatos.append({
                "equipo_local": home_name,
                "equipo_visita": away_name,
                "minuto": minuto_mostrar,
                "goles_local": home_score,
                "goles_visita": away_score,
                "liga": league_name,
                "remates": total_remates,
                "remates_puerta": total_remates_puerta,
                "presion": equipo_mas_activo,
                "tipo": "VIP" if es_vip else "GLOBAL",
                "es_descanso": is_halftime,
            })
        except Exception:
          continue

      print(
          f"✅ Extraídos {len(partidos_candidatos)} partidos de fútbol"
          " válidos.",
          flush=True,
      )
    else:
      print(f"⚠️ Status code ESPN: {response.status_code}", flush=True)

  except Exception as e:
    print(f"⚠️ Error en consulta de ESPN: {e}", flush=True)

  return partidos_candidatos


async def extraer_basket_en_vivo():
  return []
