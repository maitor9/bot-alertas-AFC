import threading
import time
from database import guardar_alerta, inicializar_db, obtener_alertas
from flask import Flask, jsonify, render_template
import requests

app = Flask(__name__)

# ==========================================
# 🔑 CONFIGURACIÓN DE APIS Y TELEGRAM
# ==========================================
API_KEY_SPORTS = "1919b9af07c4eeae00a059f0086f6473"

# FÚTBOL (API-Football)
URL_LIVE_FOOTBALL = "https://v3.football.api-sports.io/fixtures"
URL_STATS_FOOTBALL = "https://v3.football.api-sports.io/fixtures/statistics"
HEADERS_FOOTBALL = {"x-apisports-key": API_KEY_SPORTS}

# BALONCESTO (API-Basketball)
URL_LIVE_BASKET = "https://v1.basketball.api-sports.io/games"
URL_ODDS_BASKET = "https://v1.basketball.api-sports.io/odds"
HEADERS_BASKET = {"x-apisports-key": API_KEY_SPORTS}

# TELEGRAM
TELEGRAM_TOKEN = "8726477823:AAFJ5_nuDcbSxMxag2rUIjRbeuCgxqRRHh0"
TELEGRAM_CHAT_ID = "8470398609"

# ESTADOS EN MEMORIA - FÚTBOL
alertas_disparadas = set()
partidos_00_en_vivo = []
ultimas_stats_evaluadas = []

# ESTADOS EN MEMORIA - BALONCESTO
alertas_basket_disparadas = set()
partidos_basket_en_vivo = []
alertas_basket_db = []


# ==========================================
# ⚽ LÓGICA DE FÚTBOL
# ==========================================
def enviar_alerta_telegram(
    home_name, away_name, league_name, minuto, equipo_cumple
):
  if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    return

  mensaje = (
      f"🚨 <b>¡ALERTA AFC OVER 0.5 GOALS!</b> 🚨\n\n"
      f"⚽ <b>Partido:</b> {home_name} vs {away_name}\n"
      f"🏆 <b>Liga:</b> {league_name}\n"
      f"⏱ <b>Minuto:</b> {minuto}' | <b>Marcador:</b> 0 - 0\n"
      f"🔥 <b>Presión ofensiva:</b> {equipo_cumple}\n\n"
      f"📈 <i>Filtros cumplidos: Remates + Tiros a puerta en 2da mitad.</i>"
  )

  url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
  payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "HTML"}

  try:
    requests.post(url, data=payload, timeout=5)
    print(
        f"📱 Alerta Fútbol enviada a Telegram: {home_name} vs {away_name}",
        flush=True,
    )
  except Exception as e:
    print(f"⚠️ Error enviando a Telegram (Fútbol): {e}", flush=True)


def obtener_estadisticas_partido(fixture_id):
  try:
    response = requests.get(
        URL_STATS_FOOTBALL,
        headers=HEADERS_FOOTBALL,
        params={"fixture": fixture_id},
        timeout=8,
    )
    if response.status_code != 200:
      return {}
    data = response.json().get("response", [])
    if not data or len(data) < 2:
      return {}

    stats_local = {
        item["type"]: item["value"] for item in data[0]["statistics"]
    }
    stats_visita = {
        item["type"]: item["value"] for item in data[1]["statistics"]
    }

    def limpiar(val):
      if val is None:
        return 0.0
      if isinstance(val, str):
        val = val.replace("%", "")
      try:
        return float(val)
      except ValueError:
        return 0.0

    return {
        "remates_local": limpiar(stats_local.get("Total Shots")),
        "puerta_local": limpiar(stats_local.get("Shots on Goal")),
        "xg_local": limpiar(stats_local.get("expected_goals")),
        "ataques_p_local": limpiar(stats_local.get("Dangerous Attacks")),
        "remates_visita": limpiar(stats_visita.get("Total Shots")),
        "puerta_visita": limpiar(stats_visita.get("Shots on Goal")),
        "xg_visita": limpiar(stats_visita.get("expected_goals")),
        "ataques_p_visita": limpiar(stats_visita.get("Dangerous Attacks")),
    }
  except Exception as e:
    print(f"⚠️ Error obteniendo stats: {e}", flush=True)
    return {}


def evaluar_reglas_estrictas(datos):
  minuto = datos.get("minuto", 0)
  if not (46 <= minuto <= 78):
    return False, None
  if (datos.get("goles_local", 0) + datos.get("goles_visita", 0)) != 0:
    return False, None

  l_xg, l_remates, l_puerta, l_ataques = (
      datos.get("xg_local", 0.0),
      datos.get("remates_local", 0),
      datos.get("puerta_local", 0),
      datos.get("ataques_p_local", 0),
  )
  v_xg, v_remates, v_puerta, v_ataques = (
      datos.get("xg_visita", 0.0),
      datos.get("remates_visita", 0),
      datos.get("puerta_visita", 0),
      datos.get("ataques_p_visita", 0),
  )

  local_xg_ok = (l_xg >= 0.8) if l_xg > 0 else True
  cumple_local = (
      local_xg_ok
      and l_remates >= 8
      and l_puerta >= 3
      and (l_ataques >= 30 or l_ataques == 0)
  )

  visita_xg_ok = (v_xg >= 0.8) if v_xg > 0 else True
  cumple_visita = (
      visita_xg_ok
      and v_remates >= 8
      and v_puerta >= 3
      and (v_ataques >= 30 or v_ataques == 0)
  )

  if cumple_local or cumple_visita:
    equipo = datos["equipo_local"] if cumple_local else datos["equipo_visita"]
    return True, equipo
  return False, None


def bucle_escaneo():
  global partidos_00_en_vivo, ultimas_stats_evaluadas
  INTERVALO_SEGUNDOS = 300

  print("🚀 Bucle de escaneo Fútbol IA iniciado (cada 5 min)...", flush=True)

  while True:
    try:
      response = requests.get(
          URL_LIVE_FOOTBALL,
          headers=HEADERS_FOOTBALL,
          params={"live": "all"},
          timeout=10,
      )
      if response.status_code == 200:
        partidos = response.json().get("response", [])
        temp_00 = []
        candidatos_validos = []
        stats_recientes = []

        for item in partidos:
          fixture_id = item["fixture"]["id"]
          minuto = item["fixture"]["status"]["elapsed"] or 0
          goles_h = item["goals"]["home"] or 0
          goles_a = item["goals"]["away"] or 0
          home_name = item["teams"]["home"]["name"] or "Local"
          away_name = item["teams"]["away"]["name"] or "Visitante"
          league_name = item["league"]["name"] or "Liga"

          if 46 <= minuto <= 78 and (goles_h + goles_a) == 0:
            temp_00.append({
                "fixture_id": fixture_id,
                "equipo_local": home_name,
                "equipo_visita": away_name,
                "liga": league_name,
                "minuto": minuto,
            })

            if fixture_id not in alertas_disparadas:
              candidatos_validos.append((fixture_id, item, minuto))

        partidos_00_en_vivo = temp_00

        for fixture_id, item, minuto in candidatos_validos[:3]:
          home_name = item["teams"]["home"]["name"]
          away_name = item["teams"]["away"]["name"]
          league_name = item["league"]["name"]

          stats = obtener_estadisticas_partido(fixture_id)
          datos_partido = {
              "fixture_id": fixture_id,
              "equipo_local": home_name,
              "equipo_visita": away_name,
              "minuto": minuto,
              "goles_local": 0,
              "goles_visita": 0,
              **stats,
          }

          es_alerta, equipo = evaluar_reglas_estrictas(datos_partido)

          stats_recientes.append({
              "partido": f"{home_name} vs {away_name}",
              "liga": league_name,
              "minuto": minuto,
              "es_alerta": es_alerta,
              "stats": stats,
          })

          if es_alerta:
            try:
              guardar_alerta(
                  fixture_id,
                  home_name,
                  away_name,
                  league_name,
                  minuto,
                  equipo,
              )
            except Exception as e_db:
              print(f"⚠️ Error guardando en DB Fútbol: {e_db}", flush=True)

            enviar_alerta_telegram(
                home_name, away_name, league_name, minuto, equipo
            )
            alertas_disparadas.add(fixture_id)

        ultimas_stats_evaluadas = stats_recientes
    except Exception as e:
      print(f"Error escaneo Fútbol: {e}", flush=True)

    time.sleep(INTERVALO_SEGUNDOS)


# ==========================================
# 🏀 LÓGICA DE BALONCESTO CON CUOTAS REALES
# ==========================================
def enviar_alerta_telegram_basket(
    home_name, away_name, league_name, periodo, marcador, favorito, dif
):
  if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    return

  mensaje = (
      f"🏀 <b>¡ALERTA BALONCESTO - REMONTADA FAVORITO!</b> 🏀\n\n"
      f"🔥 <b>Favorito Real en Apuros:</b> {favorito} (Abajo por {dif} pts)\n"
      f"⚔️ <b>Partido:</b> {home_name} vs {away_name}\n"
      f"🏆 <b>Liga:</b> {league_name}\n"
      f"⏱ <b>Momento:</b> {periodo} | <b>Marcador:</b> {marcador}\n\n"
      f"📈 <i>Patrón Verificado: Favorito con cuotas pre-partido en desventaja"
      f" atípica. Alta probabilidad de regresión a la media.</i>"
  )

  url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
  payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "HTML"}

  try:
    requests.post(url, data=payload, timeout=5)
    print(
        f"📱 Alerta Basket enviada a Telegram: {home_name} vs {away_name}",
        flush=True,
    )
  except Exception as e:
    print(f"⚠️ Error enviando a Telegram (Basket): {e}", flush=True)


def obtener_favorito_cuotas(game_id):
  """Consulta las cuotas pre-partido para confirmar científicamente el favorito."""
  try:
    response = requests.get(
        URL_ODDS_BASKET,
        headers=HEADERS_BASKET,
        params={"game": game_id},
        timeout=8,
    )
    if response.status_code != 200:
      return None

    data = response.json().get("response", [])
    if not data:
      return None

    for bookmaker in data[0].get("bookmakers", []):
      for bet in bookmaker.get("bets", []):
        if bet.get("name") in ["Home/Away", "Match Winner"]:
          values = bet.get("values", [])
          odd_home = next(
              (
                  float(v["odd"])
                  for v in values
                  if v["value"] in ["Home", "1"]
              ),
              None,
          )
          odd_away = next(
              (
                  float(v["odd"])
                  for v in values
                  if v["value"] in ["Away", "2"]
              ),
              None,
          )

          if odd_home and odd_away:
            if odd_home < odd_away and odd_home <= 1.60:
              return "Home"
            elif odd_away < odd_home and odd_away <= 1.60:
              return "Away"
  except Exception as e:
    print(f"⚠️ Error al consultar cuotas de basket ({game_id}): {e}", flush=True)

  return None


def bucle_escaneo_basket():
  global partidos_basket_en_vivo, alertas_basket_db
  INTERVALO_SEGUNDOS = 300

  print(
      "🚀 Bucle de escaneo Baloncesto IA iniciado (Verificación de Cuotas)...",
      flush=True,
  )

  while True:
    try:
      response = requests.get(
          URL_LIVE_BASKET,
          headers=HEADERS_BASKET,
          params={"live": "all"},
          timeout=10,
      )
      if response.status_code == 200:
        games = response.json().get("response", [])
        temp_live = []

        for game in games:
          game_id = game["id"]
          league_name = game["league"]["name"]
          home_name = game["teams"]["home"]["name"]
          away_name = game["teams"]["away"]["name"]

          status_short = game.get("status", {}).get("short", "IN PROGRESS")
          scores = game.get("scores", {})
          p_home = (
              scores.get("home", {}).get("total") if scores.get("home") else 0
          )
          p_away = (
              scores.get("away", {}).get("total") if scores.get("away") else 0
          )

          p_home = p_home if p_home is not None else 0
          p_away = p_away if p_away is not None else 0
          marcador_str = f"{p_home} - {p_away}"

          temp_live.append({
              "id": game_id,
              "liga": league_name,
              "local": home_name,
              "visita": away_name,
              "marcador": marcador_str,
              "periodo": status_short,
          })

          dif = abs(p_home - p_away)

          # 1. Filtro de Momento (Q2 o HT) y Diferencia (>= 10 pts)
          if status_short in ["Q2", "HT"] and dif >= 10:
            if game_id not in alertas_basket_disparadas:

              # 2. Verificación estricta de cuotas pre-partido
              fav_real = obtener_favorito_cuotas(game_id)

              es_alerta_valida = False
              favorito_nombre = ""

              if fav_real == "Home" and p_home < p_away:
                es_alerta_valida = True
                favorito_nombre = home_name
              elif fav_real == "Away" and p_away < p_home:
                es_alerta_valida = True
                favorito_nombre = away_name

              # 3. Solo notificar si se confirma que el FAVORITO REAL va perdiendo
              if es_alerta_valida:
                alerta_obj = {
                    "liga": league_name,
                    "local": home_name,
                    "visita": away_name,
                    "marcador": marcador_str,
                    "periodo": status_short,
                    "favorito": favorito_nombre,
                    "diferencia": dif,
                }
                alertas_basket_db.append(alerta_obj)
                enviar_alerta_telegram_basket(
                    home_name,
                    away_name,
                    league_name,
                    status_short,
                    marcador_str,
                    favorito_nombre,
                    dif,
                )
                alertas_basket_disparadas.add(game_id)

        partidos_basket_en_vivo = temp_live
    except Exception as e:
      print(f"Error escaneo Basket: {e}", flush=True)

    time.sleep(INTERVALO_SEGUNDOS)


# ==========================================
# 🎨 RUTAS DE LA APLICACIÓN
# ==========================================
@app.route("/")
def index():
  return render_template("index.html")


@app.route("/api/alertas")
def api_alertas():
  try:
    alertas = obtener_alertas()
    return jsonify(alertas if alertas else [])
  except Exception as e:
    print(f"Error en API alertas: {e}", flush=True)
    return jsonify([])


@app.route("/api/partidos_00")
def api_partidos_00():
  return jsonify(partidos_00_en_vivo)


@app.route("/api/basket_alertas")
def api_basket_alertas():
  return jsonify(alertas_basket_db)


@app.route("/ver-stats")
def ver_stats():
  return jsonify(ultimas_stats_evaluadas)


@app.route("/probar-alerta")
def probar_alerta():
  try:
    home = "Real Madrid (Prueba)"
    away = "Barcelona (Prueba)"
    liga = "Liga Santander"
    minuto = 65
    equipo = "Real Madrid (Prueba)"
    fixture_id = 999999

    enviar_alerta_telegram(home, away, liga, minuto, equipo)

    try:
      guardar_alerta(fixture_id, home, away, liga, minuto, equipo)
    except Exception as db_err:
      print(f"⚠️ Nota de DB en prueba: {db_err}", flush=True)

    return "<h1>✅ Alerta de prueba ejecutada exitosamente. Revisa tu Telegram y el Dashboard.</h1>"
  except Exception as e:
    print(f"❌ Error en prueba: {e}", flush=True)
    return f"<h1>⚠ Ocurrió un error en la prueba: {e}</h1>"


@app.route("/probar-basket")
def probar_basket():
  try:
    enviar_alerta_telegram_basket(
        "Lakers (Prueba)",
        "Celtics (Prueba)",
        "NBA",
        "Q2",
        "38 - 52",
        "Lakers (Prueba)",
        14,
    )
    return "<h1>✅ Alerta de prueba de Baloncesto enviada a Telegram.</h1>"
  except Exception as e:
    print(f"❌ Error en prueba Basket: {e}", flush=True)
    return f"<h1>⚠ Error en prueba Basket: {e}</h1>"


inicializar_db()

hilo_futbol = threading.Thread(target=bucle_escaneo, daemon=True)
hilo_futbol.start()

hilo_basket = threading.Thread(target=bucle_escaneo_basket, daemon=True)
hilo_basket.start()

if __name__ == "__main__":
  app.run(host="0.0.0.0", port=5000, debug=False)
