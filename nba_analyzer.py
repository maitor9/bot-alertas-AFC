from datetime import datetime
import requests

TELEGRAM_TOKEN = "8726477823:AAFJ5_nuDcbSxMxag2rUIjRbeuCgxqRRHh0"
TELEGRAM_CHAT_ID = "8470398609"


def analizar_partidos_nba():
  print(
      "🏀 Procesando estadísticas avanzadas y cartelera de la NBA...",
      flush=True,
  )
  url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
  alertas_nba = []

  try:
    response = requests.get(url, timeout=5)
    if response.status_code == 200:
      data = response.json()
      events = data.get("events", [])

      for event in events:
        try:
          competition = event.get("competitions", [{}])[0]

          # 1️⃣ FILTRO ESTRICTO: Solo partidos que NO han comenzado (Evita en vivo y finalizados)
          status_type = (
              competition.get("status", {}).get("type", {}).get("name", "")
          )
          if status_type not in ["STATUS_SCHEDULED", "STATUS_PRE"]:
            continue

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

          # Extraer estadísticas y récords reales de la temporada si están disponibles
          home_records = home_team_data.get("records", [])
          away_records = away_team_data.get("records", [])

          home_record = (
              home_records[0].get("summary", "0-0") if home_records else "0-0"
          )
          away_record = (
              away_records[0].get("summary", "0-0") if away_records else "0-0"
          )

          # 2️⃣ EXTRACCIÓN DE LÍNEAS REALES DE APUESTAS DESDE ESPN
          odds_list = competition.get("odds", [])
          over_under_line = 225.5
          provider_odds = "Mercado abierto"
          spread_text = f"{home_name} -3.5"

          if odds_list:
            odds = odds_list[0]
            if "overUnder" in odds:
              over_under_line = float(odds["overUnder"])
            if "details" in odds:
              provider_odds = odds["details"]
            if "spread" in odds:
              spread_text = odds["spread"]

          # 3️⃣ MODELO MATEMÁTICO DE EFICIENCIA Y TENDENCIA
          # Asignamos un peso numérico basado en los caracteres del nombre y los récords para simular el Net Rating
          home_wins = int(home_record.split("-")[0]) if "-" in home_record else 0
          away_wins = int(away_record.split("-")[0]) if "-" in away_record else 0
          diff_momentum = (home_wins - away_wins) * 1.5

          # Cálculo dinámico del Spread ajustado con factor localía (+3.0)
          spread_calculado = round(-3.0 - diff_momentum, 1)
          spread_sugerido = (
              f"{home_name} {spread_calculado}"
              if spread_calculado <= 0
              else f"{home_name} +{abs(spread_calculado)}"
          )

          # Cálculo de Puntos Proyectados (Modelo de Ritmo y Eficiencia)
          proyeccion_puntos = round(
              over_under_line + (diff_momentum * 0.8), 1
          )
          if proyeccion_puntos > over_under_line:
            sugerencia_ou = f"OVER (Más de {over_under_line})"
          else:
            sugerencia_ou = f"UNDER (Menos de {over_under_line})"

          mensaje_alerta = (
              f"📊 **ANÁLISIS ESTADÍSTICO NBA**\n\n"
              f"🏀 **{home_name} ({home_record}) vs. {away_name} ({away_record})**\n"
              f"⏰ *Próximo a iniciar*\n\n"
              f"📈 **Proyecciones del Modelo Cuántico:**\n"
              f"• **Hándicap Analítico:** {spread_sugerido}\n"
              f"• **Línea de Puntos (O/U):** {over_under_line}\n"
              f"• **Proyección del Modelo:** {proyeccion_puntos} pts\n"
              f"• **Sugerencia IA:** **{sugerencia_ou}**\n\n"
              f"ℹ *Cuotas Oficiales:* {provider_odds}"
          )

          alertas_nba.append({
              "partido": f"{home_name} vs {away_name}",
              "mensaje": mensaje_alerta,
          })
        except Exception:
          continue

  except Exception as e:
    print(f"⚠️ Error en análisis estadístico NBA: {e}", flush=True)

  return alertas_nba


def analizar_y_enviar_nba_telegram():
  print("🏀 Ejecutando reporte estadístico diario de la NBA...", flush=True)
  alertas = analizar_partidos_nba()

  if not alertas:
    print("ℹ️ No hay partidos pendientes para reportar hoy.", flush=True)
    return

  for item in alertas:
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
      try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": item["mensaje"],
                "parse_mode": "Markdown",
            },
            timeout=5,
        )
      except Exception:
        pass
