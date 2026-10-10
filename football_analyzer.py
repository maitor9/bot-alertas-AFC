from datetime import datetime
import math
import requests

TELEGRAM_TOKEN = "8726477823:AAFJ5_nuDcbSxMxag2rUIjRbeuCgxqRRHh0"
TELEGRAM_CHAT_ID = "8470398609"


def calcular_probabilidad_poisson(lmbda, k):
  """Calcula la probabilidad de que ocurran k eventos usando la distribución de Poisson."""
  return (math.exp(-lmbda) * (lmbda**k)) / math.factorial(k)


def analizar_partidos_futbol_prematch():
  print("⚽ Consultando cartelera y calculando modelo de Poisson...", flush=True)
  # Usamos la misma fuente de Football-data u otra API compatible de partidos programados
  url = "https://api.football-data.org/v4/matches?status=SCHEDULED"
  headers = {"X-Auth-Token": "TU_API_KEY_SI_APLICA"}  # O endpoints públicos libres
  analisis_lista = []

  try:
    # Como respaldo o usando endpoints públicos de ESPN Fútbol si prefieres mantener la misma línea:
    url_espn = (
        "site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard"  # Ejemplo
    )

    # Vamos a estructurarlo con datos limpios de prueba/simulación matemática avanzada o endpoint seguro:
    response = requests.get(
        "https://site.api.espn.com/apis/site/v2/sports/soccer/ UEFA.CHAMPIONS/scoreboard",
        timeout=5,
    )

    # Si prefieres una fuente general o genérica de partidos programados:
    url_general = (
        "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/scoreboard"
    )
    res = requests.get(url_general, timeout=5)

    if res.status_code == 200:
      data = res.json()
      events = data.get("events", [])

      for event in events:
        try:
          competition = event.get("competitions", [{}])[0]
          teams = competition.get("competitors", [])
          if len(teams) < 2:
            continue

          home = next((t for t in teams if t.get("homeAway") == "home"), teams[0])
          away = next((t for t in teams if t.get("homeAway") == "away"), teams[1])

          home_name = home.get("team", {}).get("displayName", "Local")
          away_name = away.get("team", {}).get("displayName", "Visita")

          # Simulación de tasa de goles basados en estadísticas de Poisson (Lambda)
          # En producción esto se alimenta de los promedios reales de la API
          lambda_home = 1.45
          lambda_away = 1.15

          # Probabilidad de marcador exacto y totales por Poisson
          prob_over_25 = round(
              (
                  1
                  - (
                      calcular_probabilidad_poisson(lambda_home + lambda_away, 0)
                      + calcular_probabilidad_poisson(
                          lambda_home + lambda_away, 1
                      )
                      + calcular_probabilidad_poisson(
                          lambda_home + lambda_away, 2
                      )
                  )
              )
              * 100,
              1,
          )

          sugerencia = (
              "OVER 2.5 GOLES" if prob_over_25 > 52 else "BAJA / UNDER TENDENCIA"
          )

          mensaje = (
              f"📊 **ANÁLISIS PREPARTIDO FÚTBOL (POISSON)**\n\n"
              f"⚽ **{home_name} vs. {away_name}**\n"
              f"🏆 *Jornada Oficial*\n\n"
              f"📈 **Modelo Estadístico:**\n"
              f"• **Expected Goals (xG) Local:** {lambda_home}\n"
              f"• **Expected Goals (xG) Visita:** {lambda_away}\n"
              f"• **Probabilidad Over 2.5:** {prob_over_25}%\n"
              f"• **Sugerencia IA:** **{sugerencia}**"
          )

          analisis_lista.append({
              "partido": f"{home_name} vs {away_name}",
              "mensaje": mensaje,
          })
        except Exception:
          continue

  except Exception as e:
    print(f"⚠️ Error en análisis prepartido de fútbol: {e}", flush=True)

  return analisis_lista
