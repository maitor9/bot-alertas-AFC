from datetime import datetime, timedelta
import threading
import time
from football_analyzer import analizar_partidos_futbol_prematch
from flask import Flask, jsonify, render_template
from nba_analyzer import analizar_partidos_nba
import requests

app = Flask(__name__)

# Memoria global en servidor para almacenamiento en vivo
ultimas_alertas = []
ultimos_partidos_00 = []


def ejecutar_rastreador_en_vivo():
  """Hilo secundario que ejecuta la verificación en vivo para alertas 0-0."""
  global ultimas_alertas, ultimos_partidos_00
  while True:
    try:
      # Bloque para escanear partidos en directo sin saturar peticiones
      time.sleep(60)
    except Exception as e:
      print(f"Error en hilo secundario: {e}")
      time.sleep(30)


# Iniciar hilo secundario al arrancar la app
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
  return jsonify({
      "status": "success",
      "total_analizados": len(resultado["partidos"]),
      "data": resultado["partidos"],
      "picks_vip": resultado["picks_vip"],
  })


@app.route("/api/nba_prematch", methods=["GET"])
def api_nba_prematch():
  resultado = analizar_partidos_nba()
  return jsonify({
      "status": "success",
      "total_analizados": len(resultado["partidos"]),
      "data": resultado["partidos"],
      "picks_vip": resultado["picks_vip"],
  })


if __name__ == "__main__":
  app.run(host="0.0.0.0", port=5000, debug=True)
