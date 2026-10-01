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

# FÚTBOL (API-Football)
URL_LIVE_FOOTBALL = "https://v3.football.api-sports.io/fixtures"
URL_STATS_FOOTBALL = "https://v3.football.api-sports.io/fixtures/statistics"
HEADERS_FOOTBALL = {"x-apisports-key": API_KEY_SPORTS}

# BALONCESTO (API-Basketball)
URL_LIVE_BASKET = "https://v1.basketball.api-sports.io/games"
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
      print("🔄 Iniciando ciclo de escaneo Fútbol en API...", flush=True)
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
        print(
            f"🔎 [DIAGNÓSTICO FÚTBOL] Partidos 0-0 en min 46'-78':"
            f" {len(temp_00)}",
            flush=True,
        )

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

          print(
              f"📊 Evaluando Fútbol {home_name} vs {away_name} (Min"
              f" {minuto}') -> ¿Es Alerta?: {es_alerta}",
              flush=True,
          )

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
      else:
        print(
            f"⚠️ Error respuesta API Fútbol: Status {response.status_code}",
            flush=True,
        )
    except Exception as e:
      print(f"Error escaneo Fútbol: {e}", flush=True)

    time.sleep(INTERVALO_SEGUNDOS)


# ==========================================
# 🏀 LÓGICA DE BALONCESTO
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
    print(
        f"📱 Alerta Basket enviada a Telegram: {home_name} vs {away_name}",
        flush=True,
    )
  except Exception as e:
    print(f"⚠️ Error enviando a Telegram (Basket): {e}", flush=True)


def bucle_escaneo_basket():
  global partidos_basket_en_vivo, alertas_basket_db
  INTERVALO_SEGUNDOS = 300

  print("🚀 Bucle de escaneo Baloncesto IA iniciado (cada 5 min)...", flush=True)

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

    time.sleep(INTERVALO_SEGUNDOS)


# ==========================================
# 🎨 DISEÑO CYBERPUNK / IA & DEPORTES
# ==========================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AFC Analytics - AI Cyber Engine</title>
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Orbitron:wght@600;800;900&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #030508;
            --card-bg: rgba(10, 14, 23, 0.85);
            --card-border: rgba(245, 158, 11, 0.18);
            --accent-gold: #f59e0b;
            --accent-gold-bright: #fbbf24;
            --accent-gold-glow: rgba(245, 158, 11, 0.4);
            --accent-cyan: #06b6d4;
            --accent-orange: #f97316;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
        }

        * { box-sizing: border-box; }

        body {
            font-family: 'Space Grotesk', sans-serif;
            background-color: var(--bg-color);
            background-image: 
                radial-gradient(circle at 10% 20%, rgba(245, 158, 11, 0.07) 0%, transparent 35%),
                radial-gradient(circle at 90% 80%, rgba(6, 182, 212, 0.05) 0%, transparent 40%),
                linear-gradient(rgba(245, 158, 11, 0.03) 1px, transparent 1px),
                linear-gradient(90deg, rgba(245, 158, 11, 0.03) 1px, transparent 1px);
            background-size: 100% 100%, 100% 100%, 40px 40px, 40px 40px;
            color: var(--text-primary);
            margin: 0; padding: 0; min-height: 100vh;
        }

        .navbar {
            display: flex; justify-content: space-between; align-items: center;
            padding: 20px 6%; background: rgba(3, 5, 8, 0.9);
            backdrop-filter: blur(20px); border-bottom: 1px solid var(--card-border);
            position: sticky; top: 0; z-index: 100;
        }

        .brand { 
            display: flex; align-items: center; gap: 14px; 
            font-family: 'Orbitron', sans-serif; font-weight: 900; font-size: 22px; 
            letter-spacing: 1px; color: #fff;
        }
        .brand-icon {
            width: 42px; height: 42px;
            background: radial-gradient(circle, var(--accent-gold) 0%, rgba(245,158,11,0.15) 100%);
            border-radius: 12px; display: flex; align-items: center; justify-content: center;
            border: 1px solid var(--accent-gold); box-shadow: 0 0 20px var(--accent-gold-glow);
            font-size: 20px;
        }

        .sport-selector { display: flex; gap: 12px; }
        .sport-btn {
            background: rgba(10, 14, 23, 0.6); border: 1px solid var(--card-border);
            color: var(--text-secondary); padding: 10px 22px; border-radius: 12px;
            font-family: 'Orbitron', sans-serif; font-weight: 700; font-size: 12px;
            cursor: pointer; transition: all 0.3s ease; letter-spacing: 1px;
        }
        .sport-btn.active-football {
            background: linear-gradient(135deg, var(--accent-gold) 0%, #b45309 100%);
            color: #000; border-color: var(--accent-gold-bright);
            box-shadow: 0 4px 18px rgba(245, 158, 11, 0.4);
        }
        .sport-btn.active-basket {
            background: linear-gradient(135deg, var(--accent-orange) 0%, #c2410c 100%);
            color: #000; border-color: var(--accent-orange);
            box-shadow: 0 4px 18px rgba(249, 115, 22, 0.4);
        }

        .status-pill {
            background: rgba(245, 158, 11, 0.08); border: 1px solid var(--accent-gold);
            color: var(--accent-gold-bright); padding: 7px 18px; border-radius: 30px;
            font-family: 'Orbitron', sans-serif; font-size: 11px; font-weight: 700;
            display: flex; align-items: center; gap: 10px; letter-spacing: 1px;
            box-shadow: 0 0 15px var(--accent-gold-glow);
        }

        .pulse {
            width: 8px; height: 8px; background: var(--accent-gold-bright); border-radius: 50%;
            box-shadow: 0 0 12px var(--accent-gold-bright); animation: pulse-anim 1.8s infinite;
        }

        @keyframes pulse-anim {
            0% { transform: scale(0.9); box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.8); }
            70% { transform: scale(1.1); box-shadow: 0 0 0 10px rgba(245, 158, 11, 0); }
            100% { transform: scale(0.9); box-shadow: 0 0 0 0 rgba(245, 158, 11, 0); }
        }

        .hero-section {
            max-width: 1240px; margin: 40px auto; padding: 0 24px;
            display: grid; grid-template-columns: 1.25fr 0.75fr; gap: 40px; align-items: center;
        }

        .badge-tag {
            color: var(--accent-gold-bright); font-family: 'Orbitron', sans-serif;
            font-size: 11px; font-weight: 700; letter-spacing: 2px; text-transform: uppercase;
            margin-bottom: 14px; display: inline-block; background: rgba(245, 158, 11, 0.1);
            padding: 6px 14px; border-radius: 6px; border: 1px solid rgba(245, 158, 11, 0.3);
        }

        .hero-title { 
            font-family: 'Orbitron', sans-serif; font-size: 40px; font-weight: 900; 
            line-height: 1.2; margin: 0 0 18px 0; letter-spacing: -0.5px; 
        }
        .highlight-gold { color: var(--accent-gold-bright); text-shadow: 0 0 25px var(--accent-gold-glow); }
        .hero-desc { color: var(--text-secondary); font-size: 16px; margin-bottom: 32px; max-width: 540px; line-height: 1.6; }

        .radar-card {
            background: var(--card-bg); border: 1px solid var(--card-border);
            border-radius: 28px; padding: 35px; text-align: center; position: relative;
            box-shadow: 0 25px 50px rgba(0,0,0,0.7), inset 0 0 40px rgba(245, 158, 11, 0.04);
            backdrop-filter: blur(16px); overflow: hidden;
        }

        .radar-box {
            width: 210px; height: 210px; margin: 0 auto 24px auto; border-radius: 50%;
            border: 1px solid rgba(245, 158, 11, 0.4); position: relative;
            display: flex; align-items: center; justify-content: center;
            background: radial-gradient(circle, rgba(245,158,11,0.08) 0%, transparent 75%);
            box-shadow: 0 0 30px rgba(245, 158, 11, 0.15); overflow: hidden;
        }
        .radar-box::before { content: ''; position: absolute; width: 100%; height: 1px; background: rgba(245, 158, 11, 0.25); }
        .radar-box::after { content: ''; position: absolute; height: 100%; width: 1px; background: rgba(245, 158, 11, 0.25); }

        .radar-circle-inner { position: absolute; width: 130px; height: 130px; border-radius: 50%; border: 1px solid rgba(245, 158, 11, 0.25); }
        .radar-circle-center { position: absolute; width: 55px; height: 55px; border-radius: 50%; border: 1px solid rgba(245, 158, 11, 0.3); }

        .radar-sweep {
            position: absolute; width: 105px; height: 105px; top: 0; right: 0;
            background: conic-gradient(from 0deg at 0% 100%, rgba(245, 158, 11, 0.5) 0deg, transparent 90deg);
            border-radius: 100% 0 0 0; transform-origin: 0% 100%;
            animation: sweep 3s linear infinite;
        }
        @keyframes sweep { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }

        .blip { position: absolute; width: 7px; height: 7px; background: var(--accent-cyan); border-radius: 50%; box-shadow: 0 0 10px var(--accent-cyan); animation: blip-flash 2s infinite alternate; }
        .blip1 { top: 35%; left: 65%; animation-delay: 0.4s; }
        .blip2 { top: 68%; left: 28%; animation-delay: 1.1s; }
        @keyframes blip-flash { 0% { opacity: 0.3; transform: scale(0.8); } 100% { opacity: 1; transform: scale(1.4); } }

        .stats-counter { 
            font-family: 'Orbitron', sans-serif; font-size: 52px; font-weight: 900; 
            color: var(--accent-gold-bright); text-shadow: 0 0 20px var(--accent-gold-glow);
            margin-bottom: 2px; 
        }
        .stats-label { font-size: 11px; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 2px; font-weight: 700; }

        .main-container { max-width: 1240px; margin: 30px auto; padding: 0 24px; }
        .tabs-nav { display: flex; gap: 14px; margin-bottom: 30px; border-bottom: 1px solid var(--card-border); padding-bottom: 16px; }

        .tab-btn {
            background: rgba(10, 14, 23, 0.6); border: 1px solid var(--card-border);
            color: var(--text-secondary); padding: 14px 28px; border-radius: 16px;
            font-family: 'Orbitron', sans-serif; font-weight: 700; font-size: 13px; 
            cursor: pointer; transition: all 0.3s ease; letter-spacing: 0.5px;
            display: flex; align-items: center; gap: 12px;
        }
        .tab-btn.active {
            background: linear-gradient(135deg, var(--accent-gold) 0%, #b45309 100%); 
            color: #000; border-color: var(--accent-gold-bright);
            box-shadow: 0 6px 25px rgba(245, 158, 11, 0.4);
        }
        .tab-badge { background: rgba(0,0,0,0.3); padding: 3px 10px; border-radius: 12px; font-size: 11px; }

        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 24px; }

        .match-card {
            background: var(--card-bg); border: 1px solid var(--card-border);
            border-radius: 20px; padding: 24px; transition: all 0.3s ease;
            backdrop-filter: blur(12px); position: relative; overflow: hidden;
        }
        .match-card::before {
            content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
            background: linear-gradient(90deg, transparent, var(--accent-gold-bright), transparent);
            opacity: 0.7;
        }
        .match-card:hover {
            border-color: var(--accent-gold-bright); transform: translateY(-5px);
            box-shadow: 0 15px 35px rgba(0,0,0,0.6), 0 0 20px rgba(245, 158, 11, 0.15);
        }

        .match-meta { display: flex; justify-content: space-between; font-size: 12px; color: var(--text-secondary); margin-bottom: 14px; }
        .league-badge { background: rgba(245, 158, 11, 0.08); border: 1px solid rgba(245, 158, 11, 0.2); padding: 5px 12px; border-radius: 8px; font-weight: 600; color: var(--accent-gold-bright); }
        .minute-badge { color: var(--accent-cyan); font-weight: 800; background: rgba(6, 182, 212, 0.1); padding: 4px 10px; border-radius: 8px; font-family: 'Orbitron', sans-serif; }
        .teams-title { font-size: 19px; font-weight: 700; text-align: center; margin: 18px 0; line-height: 1.3; }

        .fulfilled-box {
            background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.3);
            padding: 12px 16px; border-radius: 14px; font-size: 13px;
            display: flex; justify-content: space-between; align-items: center;
        }
        .fulfilled-box-orange {
            background: rgba(249, 115, 22, 0.1); border: 1px solid rgba(249, 115, 22, 0.3);
            padding: 12px 16px; border-radius: 14px; font-size: 13px;
            display: flex; justify-content: space-between; align-items: center;
        }

        .team-pill { background: var(--accent-gold-bright); color: #000; font-weight: 800; padding: 4px 12px; border-radius: 8px; font-size: 12px; font-family: 'Orbitron', sans-serif; }
        .empty-card { grid-column: 1 / -1; text-align: center; padding: 70px 20px; background: var(--card-bg); border: 1px dashed var(--card-border); border-radius: 24px; color: var(--text-secondary); }

        @media (max-width: 900px) { .hero-section { grid-template-columns: 1fr; } }
    </style>
</head>
<body>

    <div class="navbar">
        <div class="brand">
            <div class="brand-icon">🧠</div>
            <span>AFC ANALYTICS AI</span>
        </div>
        
        <div class="sport-selector">
            <button id="btn-sport-futbol" class="sport-btn active-football" onclick="seleccionarDeporte('futbol')">
                ⚽ FÚTBOL
            </button>
            <button id="btn-sport-basket" class="sport-btn" onclick="seleccionarDeporte('basket')">
                🏀 BALONCESTO
            </button>
        </div>

        <div class="status-pill">
            <div class="pulse"></div>
            SYSTEM ONLINE
        </div>
    </div>

    <!-- SECCIÓN FÚTBOL -->
    <div id="seccion-futbol">
        <div class="hero-section">
            <div>
                <div class="badge-tag">Motor Algorítmico de IA - Fútbol</div>
                <h1 class="hero-title">Rastreo de Partidos 0-0 con <span class="highlight-gold">Presión Inminente</span></h1>
                <p class="hero-desc">Análisis predictivo de patrones de ataque en vivo (ventana min 46'-78') evaluando métricas avanzadas de xG, disparos directos y volumen ofensivo.</p>
            </div>

            <div class="radar-card">
                <div class="radar-box">
                    <div class="radar-circle-inner"></div>
                    <div class="radar-circle-center"></div>
                    <div class="radar-sweep"></div>
                    <div class="blip blip1"></div>
                    <div class="blip blip2"></div>
                </div>
                <div class="stats-counter" id="alertas-counter">0</div>
                <div class="stats-label">alertas confirmadas hoy</div>
            </div>
        </div>

        <div class="main-container">
            <div class="tabs-nav">
                <button class="tab-btn active" onclick="cambiarPestana(event, 'radar')">
                    📡 Radar Global 0-0 <span class="tab-badge" id="count-radar">0</span>
                </button>
                <button class="tab-btn" onclick="cambiarPestana(event, 'alertas')">
                    ⚡ Alertas VIP AI <span class="tab-badge" id="count-alertas">0</span>
                </button>
            </div>

            <div id="pestana-radar">
                <div id="grid-radar" class="grid">
                    <div class="empty-card"><h3>🔎 Buscando partidos 0-0 en ventana 46'-78'...</h3></div>
                </div>
            </div>

            <div id="pestana-alertas" style="display: none;">
                <div id="grid-alertas" class="grid">
                    <div class="empty-card"><h3>⚡ Sin alertas VIP confirmadas hoy</h3></div>
                </div>
            </div>
        </div>
    </div>

    <!-- SECCIÓN BALONCESTO -->
    <div id="seccion-basket" style="display: none;">
        <div class="hero-section">
            <div>
                <div class="badge-tag" style="color: var(--accent-orange); border-color: rgba(249, 115, 22, 0.3);">Motor Algorítmico de IA - Basket</div>
                <h1 class="hero-title">Alertas de <span class="highlight-gold" style="color: var(--accent-orange);">Remontadas en Vivo</span></h1>
                <p class="hero-desc">Detección de favoritos con desventajas de 10+ puntos en el 2º Cuarto o Descanso para aprovechar la regresión a la media.</p>
            </div>

            <div class="radar-card">
                <div class="radar-box" style="border-color: var(--accent-orange);">
                    <div class="radar-circle-inner"></div>
                    <div class="radar-circle-center"></div>
                    <div class="radar-sweep" style="background: conic-gradient(from 0deg at 0% 100%, rgba(249, 115, 22, 0.5) 0deg, transparent 90deg);"></div>
                </div>
                <div class="stats-counter" id="basket-counter" style="color: var(--accent-orange);">0</div>
                <div class="stats-label">remontadas detectadas</div>
            </div>
        </div>

        <div class="main-container">
            <div class="grid" id="grid-basket-alertas">
                <div class="empty-card"><h3>🏀 Buscando remontadas en vivo...</h3></div>
            </div>
        </div>
    </div>

    <script>
        function seleccionarDeporte(deporte) {
            const btnFutbol = document.getElementById('btn-sport-futbol');
            const btnBasket = document.getElementById('btn-sport-basket');
            const secFutbol = document.getElementById('seccion-futbol');
            const secBasket = document.getElementById('seccion-basket');

            if (deporte === 'futbol') {
                btnFutbol.className = 'sport-btn active-football';
                btnBasket.className = 'sport-btn';
                secFutbol.style.display = 'block';
                secBasket.style.display = 'none';
            } else {
                btnFutbol.className = 'sport-btn';
                btnBasket.className = 'sport-btn active-basket';
                secFutbol.style.display = 'none';
                secBasket.style.display = 'block';
            }
        }

        function cambiarPestana(evt, pestana) {
            document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
            if (evt && evt.currentTarget) {
                evt.currentTarget.classList.add('active');
            }
            if (pestana === 'radar') {
                document.getElementById('pestana-radar').style.display = 'block';
                document.getElementById('pestana-alertas').style.display = 'none';
            } else {
                document.getElementById('pestana-radar').style.display = 'none';
                document.getElementById('pestana-alertas').style.display = 'block';
            }
        }

        function cargarDatos() {
            // Cargar Fútbol 0-0
            fetch('/api/partidos_00')
                .then(res => res.json())
                .then(data => {
                    const grid = document.getElementById('grid-radar');
                    document.getElementById('count-radar').innerText = data ? data.length : 0;
                    if (!data || data.length === 0) {
                        grid.innerHTML = '<div class="empty-card"><h3>🔎 No hay partidos 0-0 en ventana 46\'-78\' actualmente</h3></div>';
                    } else {
                        grid.innerHTML = data.map(p => `
                            <div class="match-card">
                                <div class="match-meta">
                                    <span class="league-badge">🏆 ${p.liga || 'General'}</span>
                                    <span class="minute-badge">⏱️ Min ${p.minuto}'</span>
                                </div>
                                <div class="teams-title">${p.equipo_local} 0 - 0 ${p.equipo_visita}</div>
                            </div>
                        `).join('');
                    }
                });

            // Cargar Alertas Fútbol
            fetch('/api/alertas')
                .then(res => res.json())
                .then(data => {
                    const grid = document.getElementById('grid-alertas');
                    const counter = document.getElementById('alertas-counter');
                    const total = data ? data.length : 0;
                    document.getElementById('count-alertas').innerText = total;
                    counter.innerText = total;

                    if (!data || data.length === 0) {
                        grid.innerHTML = '<div class="empty-card"><h3>⚡ Sin alertas VIP confirmadas hoy</h3></div>';
                    } else {
                        grid.innerHTML = data.map(a => `
                            <div class="match-card">
                                <div class="match-meta">
                                    <span class="league-badge">🏆 ${a.liga || 'General'}</span>
                                    <span class="minute-badge">⏱️ Min ${a.minuto}'</span>
                                </div>
                                <div class="teams-title">${a.equipo_local} vs ${a.equipo_visita}</div>
                                <div class="fulfilled-box">
                                    <span>Presión IA Detectada:</span>
                                    <span class="team-pill">${a.equipo_cumple || 'Confirmado'}</span>
                                </div>
                            </div>
                        `).join('');
                    }
                });

            // Cargar Alertas Baloncesto
            fetch('/api/basket_alertas')
                .then(res => res.json())
                .then(data => {
                    const grid = document.getElementById('grid-basket-alertas');
                    const counter = document.getElementById('basket-counter');
                    const total = data ? data.length : 0;
                    counter.innerText = total;

                    if (!data || data.length === 0) {
                        grid.innerHTML = '<div class="empty-card"><h3>🏀 Sin alertas de remontada actualmente</h3></div>';
                    } else {
                        grid.innerHTML = data.map(b => `
                            <div class="match-card">
                                <div class="match-meta">
                                    <span class="league-badge">🏆 ${b.liga}</span>
                                    <span class="minute-badge" style="color: var(--accent-orange);">⏱️ ${b.periodo}</span>
                                </div>
                                <div class="teams-title">${b.local} ${b.marcador} ${b.visita}</div>
                                <div class="fulfilled-box-orange">
                                    <span>Favorito Abajo: <b>${b.favorito}</b></span>
                                    <span class="team-pill" style="background: var(--accent-orange); color: #000;">-${b.diferencia} PTS</span>
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
      print(f"⚠️️ Nota de DB en prueba: {db_err}", flush=True)

    return "<h1>✅ Alerta de prueba de Fútbol ejecutada exitosamente. Revisa Telegram y el Dashboard.</h1>"
  except Exception as e:
    print(f"❌ Error en prueba Fútbol: {e}", flush=True)
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
  print("🚀 Servidor Web Multideporte iniciado en http://127.0.0.1:5000", flush=True)
  app.run(host="0.0.0.0", port=5000, debug=False)
