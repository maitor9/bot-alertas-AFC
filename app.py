from datetime import datetime, timedelta
import threading
import time
from football_analyzer import analizar_partidos_futbol_prematch
from nba_analyzer import analizar_partidos_nba
from baseball_analyzer import analizar_partidos_baseball
from nfl_analyzer import analizar_partidos_nfl
from nhl_analyzer import analizar_partidos_nhl
from ufc_analyzer import analizar_cartelera_ufc
from motorsports_analyzer import analizar_cartelera_motor
from flask import Flask, jsonify, render_template

app = Flask(__name__)

ultimas_alertas = []
ultimos_partidos_00 = []

def ejecutar_rastreador_en_vivo():
    global ultimas_alertas, ultimos_partidos_00
    while True:
        try:
            time.sleep(60)
        except Exception as e:
            print(f"Error en hilo secundario: {e}")
            time.sleep(30)

thread_live = threading.Thread(target=ejecutar_rastreador_en_vivo, daemon=True)
thread_live.start()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/partidos_00", methods=["GET"])
def api_partidos_00():
    return jsonify(ultimos_partidos_00)

@app.route("/api/alertas", methods=["GET"])
def api_alertas():
    return jsonify(ultimas_alertas)

@app.route("/api/football_prematch", methods=["GET"])
def api_football_prematch():
    resultado = analizar_partidos_futbol_prematch()
    return jsonify({"status": "success", "total_analizados": len(resultado["partidos"]), "data": resultado["partidos"], "picks_vip": resultado["picks_vip"]})

@app.route("/api/nba_prematch", methods=["GET"])
def api_nba_prematch():
    resultado = analizar_partidos_nba()
    return jsonify({"status": "success", "total_analizados": len(resultado["partidos"]), "data": resultado["partidos"], "picks_vip": resultado["picks_vip"]})

@app.route("/api/baseball_prematch", methods=["GET"])
def api_baseball_prematch():
    resultado = analizar_partidos_baseball()
    return jsonify({"status": "success", "total_analizados": len(resultado["partidos"]), "data": resultado["partidos"], "picks_vip": resultado["picks_vip"]})

@app.route("/api/nfl_prematch", methods=["GET"])
def api_nfl_prematch():
    resultado = analizar_partidos_nfl()
    return jsonify({"status": "success", "total_analizados": len(resultado["partidos"]), "data": resultado["partidos"], "picks_vip": resultado["picks_vip"]})

@app.route("/api/nhl_prematch", methods=["GET"])
def api_nhl_prematch():
    resultado = analizar_partidos_nhl()
    return jsonify({"status": "success", "total_analizados": len(resultado["partidos"]), "data": resultado["partidos"], "picks_vip": resultado["picks_vip"]})

@app.route("/api/ufc_prematch", methods=["GET"])
def api_ufc_prematch():
    resultado = analizar_cartelera_ufc()
    return jsonify({"status": "success", "total_analizados": len(resultado["partidos"]), "data": resultado["partidos"], "picks_vip": resultado["picks_vip"]})

@app.route("/api/motor_prematch", methods=["GET"])
def api_motor_prematch():
    resultado = analizar_cartelera_motor()
    return jsonify({"status": "success", "total_analizados": len(resultado["partidos"]), "data": resultado["partidos"], "picks_vip": resultado["picks_vip"]})

@app.route("/api/mega_parley", methods=["GET"])
def api_mega_parley():
    # Extrae los 2 mejores picks VIP de TODOS los deportes
    f = analizar_partidos_futbol_prematch().get("picks_vip", [])[:2]
    b = analizar_partidos_nba().get("picks_vip", [])[:2]
    mlb = analizar_partidos_baseball().get("picks_vip", [])[:2]
    nfl = analizar_partidos_nfl().get("picks_vip", [])[:2]
    nhl = analizar_partidos_nhl().get("picks_vip", [])[:2]
    ufc = analizar_cartelera_ufc().get("picks_vip", [])[:2]
    motor = analizar_cartelera_motor().get("picks_vip", [])[:2]

    mega_list = []
    # Agrupamos todos los picks en una sola lista
    for p in (f + b + mlb + nfl + nhl + ufc + motor):
        status_symbol = " ✅" if p.get("estado_pick") == "acertado" else (" ❌" if p.get("estado_pick") == "fallado" else " ⏳")
        mega_list.append({
            "deporte": p.get("liga", "Deporte"),
            "partido": p["partido"],
            "mercado": p["mercado"],
            "prob": p["prob"],
            "status": status_symbol,
            "fecha": p.get("fecha", "📅 Fecha no disponible")
        })

    return jsonify({"status": "success", "mega_ticket": mega_list})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
