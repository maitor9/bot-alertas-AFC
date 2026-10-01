import threading
import time
from database import guardar_alerta, inicializar_db, obtener_alertas
from flask import Flask, jsonify, render_template_string
import requests

app = Flask(__name__)

# ==========================================
# 🔑 CONFIGURACIÓN DE APIS Y TELEGRAM
# ==========================================
API_KEY_SPORTS = "1919b9af07c4eeae00a059f0086f6473"

# FÚTBOL
URL_LIVE_FOOTBALL = "https://v3.football.api-sports.io/fixtures"
URL_STATS_FOOTBALL = "https://v3.football.api-sports.io/fixtures/statistics"
HEADERS_FOOTBALL = {"x-apisports-key": API_KEY_SPORTS}

# BALONCESTO
URL_LIVE_BASKET = "https://v1.basketball.api-sports.io/games"
HEADERS_BASKET = {"x-apisports-key": API_KEY_SPORTS}

# TELEGRAM
TELEGRAM_TOKEN = "8726477823:AAFJ5_nuDcbSxMxag2rUIjRbeuCgxqRRHh0"
TELEGRAM_CHAT_ID = "8470398609"

# MEMORIA
alertas_disparadas = set()
partidos_00_en_vivo = []
ultimas_stats_evaluadas = []

alertas_basket_disparadas = set()
partidos_basket_en_vivo = []
alertas_basket_db = []


# ==========================================
# ⚽ FÚTBOL
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
  except Exception as e:
    print(f"Error Telegram Fútbol: {e}", flush=True)


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
  except Exception:
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
            except Exception:
              pass
            enviar_alerta_telegram(
                home_name, away_name, league_name, minuto, equipo
            )
            alertas_disparadas.add(fixture_id)
        ultimas_stats_evaluadas = stats_recientes
    except Exception as e:
      print(f"Error escaneo Fútbol: {e}", flush=True)
    time.sleep(300)


# ==========================================
# 🏀 BALONCESTO
# ==========================================
def enviar_alerta_telegram_basket(
    home_name, away_name, league_name, periodo, marcador, favorito, dif
):
  if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    return
  mensaje = (
      f"🏀 <b>¡ALERTA BALONCESTO - REMONTADA FAVORITO!</b> 🏀\n\n"
      f"🔥 <b>Favorito en Apuros:</b> {favorito} (Abajo por {dif} pts)\n"
      f"⚔️ <b>Partido:</b> {home_name} vs {away_name}\n"
      f"🏆 <b>Liga:</b> {league_name}\n"
      f"⏱ <b>Momento:</b> {periodo} | <b>Marcador:</b> {marcador}\n\n"
      f"📈 <i>Patrón Detectado: Desviación atípica en 1ra mitad. Alta"
      f" probabilidad de regresión a la media.</i>"
  )
  url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
  payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "HTML"}
  try:
    requests.post(url, data=payload, timeout=5)
  except Exception as e:
    print(f"Error Telegram Basket: {e}", flush=True)


def bucle_escaneo_basket():
  global partidos_basket_en_vivo, alertas_basket_db
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
          if status_short in ["Q2", "HT"] and dif >= 10:
            if game_id not in alertas_basket_disparadas:
              favorito = home_name if p_home < p_away else away_name
              alerta_obj = {
                  "liga": league_name,
                  "local": home_name,
                  "visita": away_name,
                  "marcador": marcador_str,
                  "periodo": status_short,
                  "favorito": favorito,
                  "diferencia": dif,
              }
              alertas_basket_db.append(alerta_obj)
              enviar_alerta_telegram_basket(
                  home_name,
                  away_name,
                  league_name,
                  status_short,
                  marcador_str,
                  favorito,
                  dif,
              )
              alertas_basket_disparadas.add(game_id)
        partidos_basket_en_vivo = temp_live
    except Exception as e:
      print(f"Error escaneo Basket: {e}", flush=True)
    time.sleep(300)


# ==========================================
# 🎨 INTERFAZ WEB CORREGIDA (DIRECTA)
# ==========================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AFC Analytics - Multi-Sport</title>
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Orbitron:wght@600;800;900&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #030508;
            --card-bg: rgba(10, 14, 23, 0.85);
            --card-border: rgba(245, 158, 11, 0.18);
            --accent-gold: #f59e0b;
            --accent-gold-bright: #fbbf24;
            --accent-cyan: #06b6d4;
            --accent-orange: #f97316;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
        }

        * { box-sizing: border-box; }

        body {
            font-family: 'Space Grotesk', sans-serif;
            background-color: var(--bg-color);
            color: var(--text-primary);
            margin: 0; padding: 0; min-height: 100vh;
        }

        .navbar {
            display: flex; justify-content: space-between; align-items: center;
            padding: 20px 6%; background: rgba(3, 5, 8, 0.95);
            border-bottom: 1px solid var(--card-border);
            position: sticky; top: 0; z-index: 1000;
        }

        .brand { font-family: 'Orbitron', sans-serif; font-weight: 900; font-size: 22px; color: #fff; display: flex; align-items: center; gap: 10px; }

        .sport-selector { display: flex; gap: 12px; }
        .sport-btn {
            background: rgba(255, 255, 255, 0.05); border: 1px solid var(--card-border);
            color: #fff; padding: 10px 22px; border-radius: 12px;
            font-family: 'Orbitron', sans-serif; font-weight: 700; font-size: 13px;
            cursor: pointer; transition: all 0.2s ease;
        }
        .sport-btn.active-fut { background: var(--accent-gold); color: #000; border-color: var(--accent-gold-bright); }
        .sport-btn.active-bas { background: var(--accent-orange); color: #000; border-color: var(--accent-orange); }

        .main-container { max-width: 1240px; margin: 30px auto; padding: 0 24px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 24px; }

        .match-card {
            background: var(--card-bg); border: 1px solid var(--card-border);
            border-radius: 20px; padding: 24px; backdrop-filter: blur(12px);
        }

        .league-badge { background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.3); padding: 5px 12px; border-radius: 8px; font-weight: 600; color: var(--accent-gold-bright); font-size: 12px; }
        .teams-title { font-size: 19px; font-weight: 700; text-align: center; margin: 18px 0; }
        .empty-card { grid-column: 1 / -1; text-align: center; padding: 70px 20px; background: var(--card-bg); border: 1px dashed var(--card-border); border-radius: 24px; color: var(--text-secondary); }
    </style>
</head>
<body>

    <div class="navbar">
        <div class="brand">🧠 AFC ANALYTICS</div>
        <div class="sport-selector">
            <button id="btnFutbol" class="sport-btn active-fut" onclick="mostrarFutbol()">⚽ FÚTBOL</button>
            <button id="btnBasket" class="sport-btn" onclick="mostrarBasket()">🏀 BALONCESTO</button>
        </div>
    </div>

    <div class="main-container">
        <!-- VISTA FÚTBOL -->
        <div id="vistaFutbol" style="display: block;">
            <h2>⚽ Radar de Fútbol (0-0 en min 46'-78')</h2>
            <div id="gridFutbol" class="grid">
                <div class="empty-card"><h3>🔎 Buscando partidos de fútbol en vivo...</h3></div>
            </div>
        </div>

        <!-- VISTA BALONCESTO -->
        <div id="vistaBasket" style="display: none;">
            <h2>🏀 Alertas de Baloncesto (Remontada Favorito)</h2>
            <div id="gridBasket" class="grid">
                <div class="empty-card"><h3>🏀 Buscando partidos de baloncesto en vivo...</h3></div>
            </div>
        </div>
    </div>

    <script>
        function mostrarFutbol() {
            document.getElementById('vistaFutbol').style.display = 'block';
            document.getElementById('vistaBasket').style.display = 'none';
            document.getElementById('btnFutbol').className = 'sport-btn active-fut';
            document.getElementById('btnBasket').className = 'sport-btn';
        }

        function mostrarBasket() {
            document.getElementById('vistaFutbol').style.display = 'none';
            document.getElementById('vistaBasket').style.display = 'block';
            document.getElementById('btnFutbol').className = 'sport-btn';
            document.getElementById('btnBasket').className = 'sport-btn active-bas';
        }

        function cargarDatos() {
            fetch('/api/partidos_00')
                .then(r => r.json())
                .then(d => {
                    const g = document.getElementById('gridFutbol');
                    if (!d || d.length === 0) {
                        g.innerHTML = '<div class="empty-card"><h3>🔎 Sin partidos 0-0 en ventana 46\'-78\'</h3></div>';
                    } else {
                        g.innerHTML = d.map(p => `
                            <div class="match-card">
                                <div><span class="league-badge">🏆 ${p.liga}</span> ⏱️ Min ${p.minuto}'</div>
                                <div class="teams-title">${p.equipo_local} 0 - 0 ${p.equipo_visita}</div>
                            </div>
                        `).join('');
                    }
                });

            fetch('/api/basket_alertas')
                .then(r => r.json())
                .then(d => {
                    const g = document.getElementById('gridBasket');
                    if (!d || d.length === 0) {
                        g.innerHTML = '<div class="empty-card"><h3>🏀 Sin alertas de remontada en este momento</h3></div>';
                    } else {
                        g.innerHTML = d.map(b => `
                            <div class="match-card">
                                <div><span class="league-badge" style="color:var(--accent-orange);">🏆 ${b.liga}</span> ⏱️ ${b.periodo}</div>
                                <div class="teams-title">${b.local} ${b.marcador} ${b.visita}</div>
                                <div style="background:rgba(249,115,22,0.1); padding:10px; border-radius:10px;">
                                    <b>Favorito Abajo:</b> ${b.favorito} (-${b.diferencia} pts)
                                </div>
                            </div>
                        `).join('');
                    }
                });
        }

        window.onload = cargarDatos;
        setInterval(cargarDatos, 3000);
    </script>
</body>
</html>
"""


@app.route("/")
def index():
  return render_template_string(HTML_TEMPLATE)


@app.route("/api/alertas")
def api_alertas():
  try:
    return jsonify(obtener_alertas() or [])
  except Exception:
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
  enviar_alerta_telegram(
      "Real Madrid (Prueba)",
      "Barcelona (Prueba)",
      "Liga Santander",
      65,
      "Real Madrid (Prueba)",
  )
  return "<h1>✅ Alerta Fútbol enviada.</h1>"


@app.route("/probar-basket")
def probar_basket():
  enviar_alerta_telegram_basket(
      "Lakers (Prueba)",
      "Celtics (Prueba)",
      "NBA",
      "Q2",
      "38 - 52",
      "Lakers (Prueba)",
      14,
  )
  return "<h1>✅ Alerta Basket enviada.</h1>"


inicializar_db()

hilo_f = threading.Thread(target=bucle_escaneo, daemon=True)
hilo_f.start()

hilo_b = threading.Thread(target=bucle_escaneo_basket, daemon=True)
hilo_b.start()

if __name__ == "__main__":
  app.run(host="0.0.0.0", port=5000, debug=False)
