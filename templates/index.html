from datetime import datetime, timedelta
import math
import requests

TELEGRAM_TOKEN = "8726477823:AAFJ5_nuDcbSxMxag2rUIjRbeuCgxqRRHh0"
TELEGRAM_CHAT_ID = "8470398609"

LIGAS_CATALOGO = [
    # 1. El "Big Five" de Europa y sus Segundas Divisiones
    {"codigo": "eng.1", "nombre": "Premier League (Inglaterra)"},
    {"codigo": "eng.2", "nombre": "Championship (Inglaterra)"},
    {"codigo": "esp.1", "nombre": "La Liga (España)"},
    {"codigo": "esp.2", "nombre": "La Liga 2 (España)"},
    {"codigo": "ger.1", "nombre": "Bundesliga (Alemania)"},
    {"codigo": "ger.2", "nombre": "2. Bundesliga (Alemania)"},
    {"codigo": "ita.1", "nombre": "Serie A (Italia)"},
    {"codigo": "ita.2", "nombre": "Serie B (Italia)"},
    {"codigo": "fra.1", "nombre": "Ligue 1 (Francia)"},
    {"codigo": "fra.2", "nombre": "Ligue 2 (Francia)"},
    # 2. Ligas Secundarias de Alta Confiabilidad y Goles
    {"codigo": "ned.1", "nombre": "Eredivisie (Países Bajos)"},
    {"codigo": "ned.2", "nombre": "Eerste Divisie (Países Bajos)"},
    {"codigo": "por.1", "nombre": "Primeira Liga (Portugal)"},
    {"codigo": "bel.1", "nombre": "Pro League (Bélgica)"},
    {"codigo": "tur.1", "nombre": "Süper Lig (Turquía)"},
    {"codigo": "sco.1", "nombre": "Premiership (Escocia)"},
    # 3. Países Nórdicos (Escandinavia)
    {"codigo": "den.1", "nombre": "Superliga (Dinamarca)"},
    {"codigo": "swe.1", "nombre": "Allsvenskan (Suecia)"},
    {"codigo": "nor.1", "nombre": "Eliteserien (Noruega)"},
    # 4. Ligas Sudamericanas y Norteamérica
    {"codigo": "arg.1", "nombre": "Liga Profesional (Argentina)"},
    {"codigo": "bra.1", "nombre": "Brasileirão Série A (Brasil)"},
    {"codigo": "col.1", "nombre": "Liga BetPlay (Colombia)"},
    {"codigo": "mex.1", "nombre": "Liga MX (México)"},
    {"codigo": "usa.1", "nombre": "MLS (Estados Unidos)"},
    # 5. Competiciones Internacionales
    {"codigo": "uefa.champions", "nombre": "UEFA Champions League"},
    {"codigo": "uefa.europa", "nombre": "UEFA Europa League"},
    {"codigo": "uefa.conf", "nombre": "UEFA Conference League"},
    {"codigo": "conmebol.libertadores", "nombre": "Copa Libertadores"},
    {"codigo": "conmebol.sudamericana", "nombre": "Copa Sudamericana"},
]


def poisson_prob(lmbda, k):
  return (math.exp(-lmbda) * (lmbda**k)) / math.factorial(k)


def convertir_hora_colombia(date_str):
  """Convierte la fecha UTC de la API a la hora local de Colombia (UTC-5)."""
  try:
    dt_utc = datetime.strptime(date_str.replace("Z", ""), "%Y-%m-%dT%H:%M")
    dt_col = dt_utc - timedelta(hours=5)
    return dt_col.strftime("%d/%m/%Y - %H:%M")
  except Exception:
    return "📅 Próximamente"


def analizar_partidos_futbol_prematch():
  print(
      "⚽ Escaneando cartelera del día de todas las ligas globales...",
      flush=True,
  )
  analisis_lista = []
  picks_disponibles = []
  picks_altisimos = []

  for liga in LIGAS_CATALOGO:
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{liga['codigo']}/scoreboard"
    try:
      response = requests.get(url, timeout=1.5)
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

            home = next(
                (t for t in teams if t.get("homeAway") == "home"), teams[0]
            )
            away = next(
                (t for t in teams if t.get("homeAway") == "away"), teams[1]
            )

            home_name = home.get("team", {}).get("displayName", "Local")
            away_name = away.get("team", {}).get("displayName", "Visita")

            seed_h = len(home_name) % 4
            seed_a = len(away_name) % 4
            lambda_home = round(
                1.40 + (seed_h * 0.11) + (0.25 if "Chelsea" in home_name else 0),
                2,
            )
            lambda_away = round(
                1.05 + (seed_a * 0.09) + (0.20 if "Arsenal" in away_name else 0),
                2,
            )

            prob_local_win, prob_draw, prob_away_win = 0.0, 0.0, 0.0
            matrix_goals = [[0.0 for _ in range(6)] for _ in range(6)]

            for h in range(6):
              for a in range(6):
                p = poisson_prob(lambda_home, h) * poisson_prob(lambda_away, a)
                matrix_goals[h][a] = p
                if h > a:
                  prob_local_win += p
                elif h == a:
                  prob_draw += p
                else:
                  prob_away_win += p

            prob_over_15 = 0.0
            prob_over_25 = 0.0
            prob_btts = 0.0

            for h in range(6):
              for a in range(6):
                p = matrix_goals[h][a]
                if h + a >= 2:
                  prob_over_15 += p
                if h + a >= 3:
                  prob_over_25 += p
                if h > 0 and a > 0:
                  prob_btts += p

            p_win_l = round(prob_local_win * 100, 1)
            p_draw = round(prob_draw * 100, 1)
            p_win_a = round(prob_away_win * 100, 1)
            p_ov15 = round(prob_over_15 * 100, 1)
            p_ov25 = round(prob_over_25 * 100, 1)
            p_btts = round(prob_btts * 100, 1)
            p_1x = round((prob_local_win + prob_draw) * 100, 1)

            if p_ov15 >= 75.0:
              picks_altisimos.append({
                  "partido": f"{home_name} vs {away_name}",
                  "liga": liga["nombre"],
                  "mercado": "Más de 1.5 Goles",
                  "prob": p_ov15,
                  "fecha": fecha_hora_col,
              })
            if p_1x >= 75.0:
              picks_altisimos.append({
                  "partido": f"{home_name} vs {away_name}",
                  "liga": liga["nombre"],
                  "mercado": f"Doble Oportunidad (1X - {home_name} o Empate)",
                  "prob": p_1x,
                  "fecha": fecha_hora_col,
              })

            picks_disponibles.append
