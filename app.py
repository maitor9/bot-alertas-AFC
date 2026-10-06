import asyncio
import threading
import time
import requests
from datetime import datetime
from flask import Flask, jsonify, render_template
from database import inicializar_db, guardar_alerta, obtener_alertas
from scraper import extraer_futbol_en_vivo
from nba_analyzer import analizar_partidos_nba, analizar_y_enviar_nba_telegram

# 1️⃣ INICIALIZACIÓN DE LA APLICACIÓN (DEBE IR PRIMERO)
app = Flask(__name__)

# 2️⃣ RUTAS DE LA APLICACIÓN
@app.route("/api/nba_prematch", methods=["GET"])
async def api_nba_prematch():
    # Ejecuta el análisis prepartido y devuelve los reportes en formato JSON
    resultados = await analizar_partidos_nba()
    return {"status": "success", "total_analizados": len(resultados), "data": resultados}

TELEGRAM_TOKEN = "8726477823:AAFJ5_nuDcbSxMxag2rUIjRbeuCgxqRRHh0"
TELEGRAM_CHAT_ID = "8470398609"

alertas_disparadas = set()
partidos_global_en_vivo = []
partidos_vip_en_vivo = []
ultimo_escaneo_status = {"status": "Iniciando...", "timestamp": None}

def rutina_diaria_nba():
    # Bandera para asegurar que solo se envíe una vez al día
    enviado_hoy = False
    ultimo_dia = None

    while True:
        ahora = datetime.now()
        dia_actual = ahora.date()

        # Si cambia el día, reiniciamos la bandera
        if ultimo_dia != dia_actual:
            enviado_hoy = False
            ultimo_dia = dia_actual

        # Ejecutar automáticamente a las 12:00 PM (12 horas) si no se ha enviado hoy
        if ahora.hour == 12 and not enviado_hoy:
            print("⏰ Ejecutando reporte diario automático de la NBA...", flush=True)
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(analizar_y_enviar_nba_telegram())
                loop.close()
                enviado_hoy = True
            except Exception as e:
                print(f"⚠️ Error en rutina diaria NBA: {e}", flush=True)

        time.sleep(300)  # Revisa cada 5 minutos

def enviar_alerta_telegram_global(home_name, away_name, league_name, minuto_str, remates, remates_puerta, es_vip, es_descanso):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    
    if es_descanso:
        titulo = "☕ <b>¡ALERTA DESCANSO (HT) 0-0!</b> ☕"
        detalle = "⏳ <i>Partido en mediotiempo con marcador cerrado. ¡Prepárate para el 2do tiempo!</i>"
    elif es_vip:
        titulo = "⚡ <b>¡ALERTA VIP AI OVER 0.5 GOALS!</b> ⚡"
        detalle = f"📊 <b>Remates:</b> {remates} | <b>A Puerta:</b> {remates_puerta}\n🎯 <i>Cumple filtros de alta intensidad (Remates ≥8 o A puerta ≥4).</i>"
    else:
        titulo = "🚨 <b>¡ALERTA RADAR GLOBAL 0-0!</b> 🚨"
        detalle = f"⏱ <i>Partido en juego (Minuto 46'-80') con marcador 0-0.</i>"

    mensaje = (
        f"{titulo}\n\n"
        f"⚽ <b>Partido:</b> {home_name} vs {away_name}\n"
        f"🏆 <b>Liga:</b> {league_name}\n"
        f"⏱ <b>Momento:</b> {minuto_str} | <b>Marcador:</b> 0 - 0\n"
        f"{detalle}"
    )
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "HTML"},
            timeout=5
        )
    except Exception as e:
        print(f"⚠️ Error Telegram Global: {e}", flush=True)

def bucle_escaneo_unificado():
    global partidos_global_en_vivo, partidos_vip_en_vivo, ultimo_escaneo_status
    print("🚀 Bucle de escaneo general iniciado...", flush=True)

    while True:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            print("🔄 Consultando partidos (Juego y Descanso)...", flush=True)
            candidatos = loop.run_until_complete(extraer_futbol_en_vivo())
            
            global_list = []
            vip_list = []

            for p in candidatos:
                global_list.append(p)

                es_vip = (p.get('tipo') == "VIP")
                if es_vip:
                    vip_list.append(p)

                # Identificador único por partido
                partido_id = f"{p['equipo_local']}_{p['equipo_visita']}"
                
                if partido_id not in alertas_disparadas:
                    try:
                        guardar_alerta(partido_id, p['equipo_local'], p['equipo_visita'], p['liga'], str(p['minuto']), p['presion'])
                    except Exception:
                        pass
                    
                    enviar_alerta_telegram_global(
                        p['equipo_local'], 
                        p['equipo_visita'], 
                        p['liga'], 
                        p['minuto'], 
                        p.get('remates', 0), 
                        p.get('remates_puerta', 0), 
                        es_vip,
                        p.get('es_descanso', False)
                    )
                    alertas_disparadas.add(partido_id)

            partidos_global_en_vivo = global_list
            partidos_vip_en_vivo = vip_list

            ultimo_escaneo_status = {
                "status": "OK",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "global_count": len(global_list),
                "vip_count": len(vip_list)
            }
            print(f"✨ Ciclo completado a las {ultimo_escaneo_status['timestamp']}", flush=True)

        except Exception as e:
            print(f"⚠️ Error crítico en bucle: {e}", flush=True)
            ultimo_escaneo_status = {
                "status": "ERROR",
                "detalle": str(e),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
        finally:
            loop.close()

        time.sleep(60)

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
    return jsonify(partidos_global_en_vivo)

@app.route('/api/vip_alertas')
def api_vip_alertas():
    return jsonify(partidos_vip_en_vivo)

@app.route('/api/basket_alertas')
def api_basket_alertas():
    return jsonify([])

@app.route('/probar-scraper')
def probar_scraper():
    return jsonify({
        "estado_servicio": "Servidor Activo",
        "ultimo_escaneo": ultimo_escaneo_status,
        "radar_global_00": len(partidos_global_en_vivo),
        "alertas_vip_ai": len(partidos_vip_en_vivo)
    })

inicializar_db()

hilo_unificado = threading.Thread(target=bucle_escaneo_unificado, daemon=True)
hilo_unificado.start()

# Hilo para el reporte automático diario de la NBA
hilo_nba_diario = threading.Thread(target=rutina_diaria_nba, daemon=True)
hilo_nba_diario.start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
