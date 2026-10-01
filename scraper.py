import asyncio
import threading
import time
import requests
from flask import Flask, jsonify, render_template
from database import inicializar_db, guardar_alerta, obtener_alertas
from scraper import extraer_futbol_en_vivo, extraer_basket_en_vivo

app = Flask(__name__)

TELEGRAM_TOKEN = "8726477823:AAFJ5_nuDcbSxMxag2rUIjRbeuCgxqRRHh0"
TELEGRAM_CHAT_ID = "8470398609"

alertas_disparadas = set()
partidos_00_en_vivo = []
alertas_basket_disparadas = set()
alertas_basket_db = []
ultimo_escaneo_status = {"status": "Iniciando...", "timestamp": None}

def enviar_alerta_telegram_futbol(home_name, away_name, league_name, minuto, equipo_cumple):
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
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "HTML"},
            timeout=5
        )
    except Exception as e:
        print(f"⚠️ Error Telegram Fútbol: {e}", flush=True)

def enviar_alerta_telegram_basket(home_name, away_name, league_name, periodo, marcador, favorito, dif):
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
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "HTML"},
            timeout=5
        )
    except Exception as e:
        print(f"⚠️ Error Telegram Basket: {e}", flush=True)

def bucle_escaneo_unificado():
    global partidos_00_en_vivo, alertas_basket_db, ultimo_escaneo_status
    print("🚀 Bucle unificado de escaneo iniciado...", flush=True)

    while True:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            print("🔄 Iniciando ciclo de scraping...", flush=True)
            candidatos_futbol = loop.run_until_complete(extraer_futbol_en_vivo())
            partidos_00_en_vivo = candidatos_futbol

            for p in candidatos_futbol:
                partido_id = f"{p['equipo_local']}_{p['equipo_visita']}"
                if partido_id not in alertas_disparadas:
                    try:
                        guardar_alerta(partido_id, p['equipo_local'], p['equipo_visita'], p['liga'], p['minuto'], p['equipo_local'])
                    except Exception:
                        pass
                    enviar_alerta_telegram_futbol(p['equipo_local'], p['equipo_visita'], p['liga'], p['minuto'], p['equipo_local'])
                    alertas_disparadas.add(partido_id)

            candidatos_basket = loop.run_until_complete(extraer_basket_en_vivo())
            for b in candidatos_basket:
                game_id = f"{b['local']}_{b['visita']}"
                if game_id not in alertas_basket_disparadas:
                    alertas_basket_db.append(b)
                    enviar_alerta_telegram_basket(b['local'], b['visita'], b['liga'], b['periodo'], b['marcador'], b['favorito'], b['diferencia'])
                    alertas_basket_disparadas.add(game_id)

            ultimo_escaneo_status = {
                "status": "OK",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "futbol_count": len(candidatos_futbol),
                "basket_count": len(candidatos_basket)
            }
            print(f"✨ Ciclo completado con éxito a las {ultimo_escaneo_status['timestamp']}", flush=True)

        except Exception as e:
            print(f"⚠️ Error crítico en bucle unificado: {e}", flush=True)
            ultimo_escaneo_status = {
                "status": "ERROR",
                "detalle": str(e),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
        finally:
            loop.close()

        time.sleep(120)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/alertas')
def api_alertas():
    try:
        alertas = obtener_alertas()
        return jsonify(alertas if alertas else [])
    except Exception:
        return jsonify([])

@app.route('/api/partidos_00')
def api_partidos_00():
    return jsonify(partidos_00_en_vivo)

@app.route('/api/basket_alertas')
def api_basket_alertas():
    return jsonify(alertas_basket_db)

@app.route('/probar-scraper')
def probar_scraper():
    return jsonify({
        "estado_servicio": "Servidor Activo",
        "ultimo_escaneo": ultimo_escaneo_status,
        "futbol_candidatos_detectados": partidos_00_en_vivo,
        "basket_candidatos_detectados": alertas_basket_db
    })

inicializar_db()

hilo_unificado = threading.Thread(target=bucle_escaneo_unificado, daemon=True)
hilo_unificado.start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
