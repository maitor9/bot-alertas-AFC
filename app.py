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
from yellow_cards_analyzer import analizar_alertas_tarjetas
from odds_tracker import generar_parley_optimo, obtener_historial_parleys
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

@app.route("/api/tarjetas_alerta", methods=["GET"])
def api_tarjetas_alerta():
    resultado = analizar_alertas_tarjetas()
    return jsonify({
        "status": "success", 
        "total_alertas": len(resultado), 
        "alertas": resultado
    })

@app.route("/api/parley_optimo", methods=["GET"])
def api_parley_optimo():
    resultado_parley = generar_parley_optimo(target_cuota=1.50)
    return jsonify(resultado_parley)

@app.route("/api/historial_parleys", methods=["GET"])
def api_historial_parleys():
    historial = obtener_historial_parleys()
    return jsonify({
        "status": "success",
        "total": len(historial),
        "historial": historial
    })

@app.route("/api/football_prematch", methods=["GET"])
def api_football_prematch():
    resultado = analizar_partidos_futbol_prematch()
    for item in resultado.get("raw_picks", []):
        f_val = item.get("fecha") or item.get("time") or item.get("datetime") or "📅 Próximamente"
        item["fecha"] = f_val
        item["time"] = f_val
        item["datetime"] = f_val

    return jsonify({
        "status": "success", 
        "total_analizados": len(resultado["partidos"]), 
        "data": resultado["partidos"], 
        "picks_vip": resultado["picks_vip"],
        "raw_picks": resultado.get("raw_picks", [])
    })

@app.route("/api/nba_prematch", methods=["GET"])
def api_nba_prematch():
    resultado = analizar_partidos_nba()
    for item in resultado.get("raw_picks", []):
        f_val = item.get("fecha") or item.get("time") or item.get("datetime") or "📅 Próximamente"
        item["fecha"] = f_val
        item["time"] = f_val
        item["datetime"] = f_val

    return jsonify({
        "status": "success", 
        "total_analizados": len(resultado["partidos"]), 
        "data": resultado["partidos"], 
        "picks_vip": resultado["picks_vip"],
        "raw_picks": resultado.get("raw_picks", [])
    })

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
    return jsonify({"status": "success", "total_analizados": len(resultado["partidos"]), "data": resultado["data"], "picks_vip": resultado["picks_vip"]})

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
    f = analizar_partidos_futbol_prematch().get("picks_vip", [])[:2]
    b = analizar_partidos_nba().get("picks_vip", [])[:2]
    mlb = analizar_partidos_baseball().get("picks_vip", [])[:2]
    nfl = analizar_partidos_nfl().get("picks_vip", [])[:2]
    nhl = analizar_partidos_nhl().get("picks_vip", [])[:2]
    ufc = analizar_cartelera_ufc().get("picks_vip", [])[:2]
    motor = analizar_cartelera_motor().get("picks_vip", [])[:2]

    mega_list = []
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
    app.run(host="0.0.0.0", port=10000, debug=True)
