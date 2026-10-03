import re
import requests


# ==========================================
# ⚽ SCRAPER VIP ESTRICTO (MIN 46-80, 0-0, REMATES >=8 Y A PUERTA >=4)
# ==========================================
async def extraer_futbol_en_vivo():
  partidos_candidatos = []
  print(
      "⏳ Consultando API de ESPN con filtro estricto (Remates >=8 Y A puerta"
      " >=4)...",
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

          # Excluir otros deportes
          if (
              "basketball" in league_lower
              or "baloncesto" in league_lower
              or "nba" in league_lower
              or "ncaa" in league_lower
          ):
            continue

          status = event.get("status", {})
          state = status.get("type", {}).get("state", "")

          # Solo partidos en juego ("in")
          if state != "in":
            continue

          display_clock = status.get("displayClock", "0")
          min_int = 0
          match_min = re.search(r"\d+", str(display_clock))
          if match_min:
            min_int = int(match_min.group())

          # Regla de Tiempo: Estrictamente desde el minuto 46 hasta el 80
          if not (46 <= min_int <= 80):
            continue

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

          # Regla 1: Total de goles del partido igual a 0
          if (home_score + away_score) != 0:
            continue

          # Regla 2 & 3 (ESTRICTO CON Y / AND): Remates totales >= 8 Y Remates a puerta >= 4
          condicion_remates_estricta = (total_remates >= 8) and (
              total_remates_puerta >= 4
          )
          if not condicion_remates_estricta:
            continue

          # Si cumple rigurosamente todo, se envía al bloque VIP
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
          f"✅ Extraídos {len(partidos_candidatos)} partidos bajo la regla"
          " estricta (Y).",
          flush=True,
      )
    else:
      print(f"⚠️ Status code ESPN: {response.status_code}", flush=True)

  except Exception as e:
    print(f"⚠️ Error en consulta de ESPN: {e}", flush=True)

  return partidos_candidatos


async def extraer_basket_en_vivo():
  return []
