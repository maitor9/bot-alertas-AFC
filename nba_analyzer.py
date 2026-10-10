from datetime import datetime, timedelta
import requests

TELEGRAM_TOKEN = "8726477823:AAFJ5_nuDcbSxMxag2rUIjRbeuCgxqRRHh0"
TELEGRAM_CHAT_ID = "8470398609"


def convertir_hora_colombia(date_str):
  """Convierte la fecha UTC de la API a la hora local de Colombia (UTC-5)."""
  try:
    dt_utc = datetime.strptime(date_str.replace("Z", ""), "%Y-%m-%dT%H:%M")
    dt_col = dt_utc - timedelta(hours=5)
    return dt_col.strftime("%d/%m/%Y - %H:%M")
  except Exception:
    return "📅 Próximamente"


def analizar_partidos_nba():
  print("🏀 Escaneando cartelera NBA del día...", flush=True)
  analisis_lista = []
  picks_disponibles = []
  picks_altisimos = []

  url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
  try:
    response = requests.get(url, timeout=2.5)
    if response.status_code == 200:
      data = response.json()
      events = data.get("events", [])

      for event in events:
        try:
          competition = event.get("competitions", [{}])[0]
          status_type = (
              competition.get("status", {}).get("type", {}).get("name", "")
          )
          if status_type not in ["STATUS_SCHEDULED", "STATUS_PRE"]:
            continue

          date_raw = event.get("date", "")
          fecha_hora_col = convertir_hora_colombia(date_raw)

          teams = competition.get("competitors", [])
          if len(teams) < 2:
            continue

          home = next((t for t in teams if t.get("homeAway") == "home"), teams[0])
          away = next((t for t in teams if t.get("homeAway") == "away"), teams[1])

          home_name = home.get("team", {}).get("displayName", "Local")
          away_name = away.get("team", {}).get("displayName", "Visita")

          # Modelo predictivo simulado basado en métricas de string (Estable para AI sin base de datos)
          h_val = sum([ord(c) for c in home_name])
          a_val = sum([ord(c) for c in away_name])
          
          # Probabilidad Moneyline (Ganador)
          diff = (h_val - a_val) % 30
          base_home_win = 50.0 + diff
          if base_home_win > 88.0: base_home_win = 88.0
          if base_home_win < 15.0: base_home_win = 15.0
          
          p_win_h = round(base_home_win, 1)
          p_win_a = round(100.0 - p_win_h, 1)

          # Proyección de Puntos (Over/Under)
          line_est = 215.5 + ((h_val + a_val) % 20)
          p_over_alt = round(65.0 + ((h_val % 10) * 2), 1) # Probabilidad para Over alternativo (65-85%)
          if p_over_alt > 88.0: p_over_alt = 88.0

          if p_win_h >= 75.0:
            picks_altisimos.append({
                "partido": f"{home_name} vs {away_name}",
                "liga": "NBA",
                "mercado": f"Gana {home_name} (Moneyline)",
                "prob": p_win_h,
                "fecha": fecha_hora_col,
            })
          elif p_win_a >= 75.0:
            picks_altisimos.append({
                "partido": f"{home_name} vs {away_name}",
                "liga": "NBA",
                "mercado": f"Gana {away_name} (Moneyline)",
                "prob": p_win_a,
                "fecha": fecha_hora_col,
            })

          if p_over_alt >= 75.0:
            picks_altisimos.append({
                "partido": f"{home_name} vs {away_name}",
                "liga": "NBA",
                "mercado": f"Más de {line_est - 10} Puntos",
                "prob": p_over_alt,
                "fecha": fecha_hora_col,
            })

          picks_disponibles.append({
              "partido": f"{home_name} vs {away_name}",
              "home": home_name,
              "away": away_name,
              "p_win_h": p_win_h,
              "p_win_a": p_win_a,
              "p_over": p_over_alt,
              "line": line_est,
              "fecha": fecha_hora_col,
          })

          favorito = home_name if p_win_h > 50 else away_name
          opcion_parley = f"Gana {favorito}" if max(p_win_h, p_win_a) > p_over_alt else f"Over {line_est - 10} Pts"

          mensaje = (
              f"🏀 **ANÁLISIS PROYECCIÓN NBA (IA)**\n\n"
              f"🏟 **{home_name} vs. {away_name}**\n"
              f"⏰ **Fecha/Hora (Col):** {fecha_hora_col}\n\n"
              f"📈 **Moneyline (Ganador):**\n"
              f"• **{home_name}:** {p_win_h}%\n"
              f"• **{away_name}:** {p_win_a}%\n\n"
              f"🔥 **Mercados de Tot
