from datetime import datetime
import requests

TELEGRAM_TOKEN = "8726477823:AAFJ5_nuDcbSxMxag2rUIjRbeuCgxqRRHh0"
TELEGRAM_CHAT_ID = "8470398609"


def analizar_partidos_nba():
  print(
      "🏀 Consultando partidos y estadísticas prepartido de la NBA...",
      flush=True,
  )
  url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
  alertas_nba = []

  try:
    response = requests.get(url, timeout=10)
    print(f"🔍 Status code ESPN NBA: {response.status_code}", flush=True)

    if response.status_code == 200:
      data = response.json()
      events = data.get("events", [])

      for event in events:
        try:
          competition = event.get("competitions", [{}])[0]
          teams = competition.get("competitors", [])
          if len(teams) < 2:
            continue

          home_team_data = next(
              (t for t in teams if t.get("homeAway") == "home"), teams[0]
          )
          away_team_data = next(
              (t for t in teams if t.get("homeAway") == "away"), teams[1]
          )

          home_name = home_team_data.get("team", {}).get(
              "displayName", "Local"
          )
          away_name = away_team_data.get("team", {}).get(
              "displayName", "Visita"
          )

          home_record = (
              home_team_data.get("records", [{}])[0].get("summary", "0-0")
          )
          away_record = (
              away_team_data.get("records", [{}])[0].get("summary", "0-0")
          )

          odds = competition.get("odds", [{}])[0]
          provider_odds = odds.get("details", "Línea estándar")
          over_under_line = odds.get("overUnder", 225.5)

          proyeccion_total = float(over_under_line)
          sugerencia_ou = (
              "OVER (Más de)" if proyeccion_total > 220 else "UNDER (Menos de)"
          )
          spread_sugerido = f"{home_name} -4.5"

          mensaje_alerta = (
              f"📊 **ANÁLISIS PREPARTIDO NBA**\n\n"
              f"🏀 **{home_name} ({home_record}) vs. {away_name} ({away_record})**\n"
              f"⏰ *Jornada de hoy*\n\n"
              f"📈 **Proyecciones del Modelo:**\n"
              f"• **Hándicap Sugerido:** {spread_sugerido}\n"
              f"• **Línea de Puntos (O/U):** {over_under_line}\n"
              f"• **Sugerencia:** **{sugerencia_ou}**\n\n"
              f"ℹ *Cuotas Mercado:* {provider_odds}"
          )

          alertas_nba.append({
              "partido": f"{home_name} vs {away_name}",
              "mensaje": mensaje_alerta,
          })
        except Exception:
          continue

      print(
          f"✅ Análisis NBA completado. Partidos evaluados:"
          f" {len(alertas_nba)}",
          flush=True,
      )

  except Exception as e:
    print(f"⚠️ Error conectando con la API de NBA ESPN: {e}", flush=True)

  return alertas_nba


def analizar_y_enviar_nba_telegram():
  print(
      "🏀 Consultando partidos y estadísticas prepartido de la NBA para"
      " Telegram...",
      flush=True,
  )
  url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
  alertas_nba = []

  try:
    response = requests.get(url, timeout=10)
    if response.status_code == 200:
      data = response.json()
      events = data.get("events", [])

      for event in events:
        try:
          competition = event.get("competitions", [{}])[0]
          teams = competition.get("competitors", [])
          if len(teams) < 2:
            continue

          home_team_data = next(
              (t for t in teams if t.get("homeAway") == "home"), teams[0]
          )
          away_team_data = next(
              (t for t in teams if t.get("homeAway") == "away"), teams[1]
          )

          home_name = home_team_data.get("team", {}).get(
              "displayName", "Local"
          )
          away_name = away_team_data.get("team", {}).get(
              "displayName", "Visita"
          )

          home_record = (
              home_team_data.get("records", [{}])[0].get("summary", "0-0")
          )
          away_record = (
              away_team_data.get("records", [{}])[0].get("summary", "0-0")
          )

          odds = competition.get("odds", [{}])[0]
          provider_odds = odds.get("details", "Línea estándar")
          over_under_line = odds.get("overUnder", 225.5)

          proyeccion_total = float(over_under_line)
          sugerencia_ou = (
              "OVER (Más de)" if proyeccion_total > 220 else "UNDER (Menos de)"
          )
          spread_sugerido = f"{home_name} -4.5"

          mensaje_alerta = (
              f"📊 **ANÁLISIS PREPARTIDO NBA**\n\n"
              f"🏀 **{home_name} ({home_record}) vs. {away_name} ({away_record})**\n"
              f"⏰ *Jornada de hoy*\n\n"
              f"📈 **Proyecciones del Modelo:**\n"
              f"• **Hándicap Sugerido:** {spread_sugerido}\n"
              f"• **Línea de Puntos (O/U):** {over_under_line}\n"
              f"• **Sugerencia:** **{sugerencia_ou}**\n\n"
              f"ℹ *Cuotas Mercado:* {provider_odds}"
          )

          if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                data={
                    "chat_id": TELEGRAM_CHAT_ID,
                    "text": mensaje_alerta,
                    "parse_mode": "Markdown",
                },
                timeout=5,
            )

          alertas_nba.append({
              "partido": f"{home_name} vs {away_name}",
              "mensaje": mensaje_alerta,
          })
        except Exception:
          continue

  except Exception as e:
    print(f"⚠️ Error en análisis NBA Telegram: {e}", flush=True)

  return alertas_nba
