import asyncio
import threading
import time
from database import guardar_alerta, inicializar_db, obtener_alertas
from flask import Flask, jsonify, render_template
import requests
from scraper import extraer_basket_en_vivo, extraer_futbol_en_vivo

app = Flask(__name__)

# ==========================================
# 🔑 CONFIGURACIÓN DE TELEGRAM
# ==========================================
TELEGRAM_TOKEN = "8726477823:AAFJ5_nuDcbSxMxag2rUIjRbeuCgxqRRHh0"
TELEGRAM_CHAT_ID = "8470398609"

# ESTADOS EN MEMORIA - FÚTBOL
alertas_disparadas = set()
partidos_00_en_vivo = []

# ESTADOS EN MEMORIA - BALONCESTO
alertas_basket_disparadas = set()
alertas_basket_db = []


# ==========================================
# ⚽ ENVÍO Y BUCLE DE FÚTBOL (SCRAPING)
# ==========================================
def enviar_alerta_telegram_futbol(
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
      f"📈 <i>Detectado vía Scraper autónomo en 2da mitad.</i>"
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
    print(f"⚠️️ Error enviando a Telegram (Fútbol): {e}", flush=True)


def bucle_escaneo_futbol():
  global partidos_00_en_vivo
  INTERVALO_SEGUNDOS = 180  # Escaneo cada 3 minutos (100% Gratis e ilimitado)

  print("🚀 Bucle de escaneo Fútbol con Scraper iniciado...", flush=True)

  while True:
    try:
      # Ejecutamos la función asíncrona de Playwright desde el hilo sincrónico
      candidatos = asyncio.run(extraer_futbol_en_vivo())
      partidos_00_en_vivo = candidatos

      for p in candidatos:
        partido_id = f"{p['equipo_local']}_{p['equipo_visita']}"

        if partido_id not in alertas_disparadas:
          equipo_presion = p["equipo_local"]
          try:
            guardar_alerta(
                partido_id,
                p["equipo_local"],
                p["equipo_visita"],
                p["liga"],
                p["minuto"],
                equipo_presion,
            )
          except Exception as e_db:
            print(f"⚠️ Error DB Fútbol: {e_db}", flush=True)

          enviar_alerta_telegram_futbol(
              p["equipo_local"],
              p["equipo_visita"],
              p["liga"],
              p["minuto"],
              equipo_presion,
          )
          alertas_disparadas.add(partido_id)

    except Exception as e:
      print(f"⚠️ Error en ciclo de scraping Fútbol: {e}", flush=True)

    time.sleep(INTERVALO_SEGUNDOS)


# ==========================================
# 🏀 ENVÍO Y BUCLE DE BALONCESTO (SCRAPING)
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
      f"📈 <i>Desventaja atípica detectada en 1ra mitad vía Scraper.</i>"
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
  global alertas_basket_db
  INTERVALO_SEGUNDOS = 180  # Escaneo cada 3 minutos

  print("🚀 Bucle de escaneo Baloncesto con Scraper iniciado...", flush=True)

  while True:
    try:
      candidatos = asyncio.run(extraer_basket_en_vivo())

      for b in candidatos:
        game_id = f"{b['local']}_{b['visita']}"

        if game_id not in alertas_basket_disparadas:
          alerta_obj = {
              "liga": b["liga"],
              "local": b["local"],
              "visita": b["visita"],
              "marcador": b["marcador"],
              "periodo": b["periodo"],
              "favorito": b["favorito"],
              "diferencia": b["diferencia"],
          }
          alertas_basket_db.append(alerta_obj)
          enviar_alerta_telegram_basket(
              b["local"],
              b["visita"],
              b["liga"],
              b["periodo"],
              b["marcador"],
              b["favorito"],
              b["diferencia"],
          )
          alertas_basket_disparadas.add(game_id)

    except Exception as e:
      print(f"⚠️ Error en ciclo de scraping Basket: {e}", flush=True)

    time.sleep(INTERVALO_SEGUNDOS)


# ==========================================
# 🎨 RUTAS DE LA APLICACIÓN WEB
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


@app.route("/probar-alerta")
def probar_alerta():
  try:
    home = "Real Madrid (Prueba Scraper)"
    away = "Barcelona (Prueba Scraper)"
    liga = "Liga Santander"
    minuto = 65
    equipo = "Real Madrid (Prueba Scraper)"
    fixture_id = "test_999999"

    enviar_alerta_telegram_futbol(home, away, liga, minuto, equipo)

    try:
      guardar_alerta(fixture_id, home, away, liga, minuto, equipo)
    except Exception as db_err:
      print(f"⚠️️ DB Prueba: {db_err}", flush=True)

    return "<h1>✅ Alerta de prueba de Fútbol enviada a Telegram.</h1>"
  except Exception as e:
    return f"<h1>⚠️ Error en prueba: {e}</h1>"


@app.route("/probar-basket")
def probar_basket():
  try:
    enviar_alerta_telegram_basket(
        "Lakers (Prueba Scraper)",
        "Celtics (Prueba Scraper)",
        "NBA",
        "Q2",
        "38 - 52",
        "Lakers (Prueba Scraper)",
        14,
    )
    return "<h1>✅ Alerta de prueba de Baloncesto enviada a Telegram.</h1>"
  except Exception as e:
    return f"<h1>⚠️ Error en prueba Basket: {e}</h1>"


# Inicializar Base de Datos y lanzar Hilos
inicializar_db()

hilo_futbol = threading.Thread(target=bucle_escaneo_futbol, daemon=True)
hilo_futbol.start()

hilo_basket = threading.Thread(target=bucle_escaneo_basket, daemon=True)
hilo_basket.start()

if __name__ == "__main__":
  app.run(host="0.0.0.0", port=5000, debug=False)
