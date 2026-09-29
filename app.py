import threading
import time
from database import guardar_alerta, inicializar_db, obtener_alertas
from flask import Flask, jsonify, render_template_string
import requests

app = Flask(__name__)

# ==========================================
# 🔑 CONFIGURACIÓN DE APIS Y TELEGRAM
# ==========================================
API_KEY = "1919b9af07c4eeae00a059f0086f6473"
URL_LIVE = "https://v3.football.api-sports.io/fixtures"
URL_STATS = "https://v3.football.api-sports.io/fixtures/statistics"
HEADERS = {"x-apisports-key": API_KEY}

# CREDENCIALES DE TELEGRAM
TELEGRAM_TOKEN = "8726477823:AAFJ5_nuDcbSxMxag2rUIjRbeuCgxqRRHh0"
TELEGRAM_CHAT_ID = (
    "PEGA_AQUI_TU_CHAT_ID"  # Reemplaza con tu Chat ID de Telegram
)

alertas_disparadas = set()


def enviar_alerta_telegram(
    home_name, away_name, league_name, minuto, equipo_cumple
):
    """Envía un mensaje con formato profesional a Telegram."""
    if (
        TELEGRAM_TOKEN == "PEGA_AQUI_TU_TELEGRAM_TOKEN"
        or not TELEGRAM_TOKEN
        or TELEGRAM_CHAT_ID == "PEGA_AQUI_TU_CHAT_ID"
    ):
        print("⚠️ Telegram no configurado correctamente. Omite envío.")
        return

    mensaje = (
        f"🚨 <b>¡ALERTA OVER 0.5 GOALS!</b> 🚨\n\n"
        f"⚽ <b>Partido:</b> {home_name} vs {away_name}\n"
        f"🏆 <b>Liga:</b> {league_name}\n"
        f"⏱️ <b>Minuto:</b> {minuto}' | <b>Marcador:</b> 0 - 0\n"
        f"🔥 <b>Presión ofensiva:</b> {equipo_cumple}\n\n"
        f"📈 <i>Filtros cumplidos: xG/Tiros + Marcador 0-0 en 2da mitad.</i>"
    )

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje,
        "parse_mode": "HTML",
    }

    try:
        requests.post(url, data=payload, timeout=5)
        print(f"📱 Alerta enviada a Telegram: {home_name} vs {away_name}")
    except Exception as e:
        print(f"⚠️ Error enviando a Telegram: {e}")


def obtener_estadisticas_partido(fixture_id):
    try:
        response = requests.get(
            URL_STATS,
            headers=HEADERS,
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

    local_xg_ok = (l_xg >= 0.8) if l_xg > 0 else (l_remates >= 8)
    cumple_local = (
        local_xg_ok
        and l_remates >= 8
        and l_puerta >= 3
        and (l_ataques >= 30 or l_ataques == 0)
    )

    visita_xg_ok = (v_xg >= 0.8) if v_xg > 0 else (v_remates >= 8)
    cumple_visita = (
        visita_xg_ok
        and v_remates >= 8
        and v_puerta >= 3
        and (v_ataques >= 30 or v_ataques == 0)
    )

    if cumple_local or cumple_visita:
        equipo = (
            datos["equipo_local"] if cumple_local else datos["equipo_visita"]
        )
        return True, equipo
    return False, None


def bucle_escaneo():
    """Escáner optimizado (cada 10 min) para maximizar el cupo diario de 100 peticiones."""
    INTERVALO_SEGUNDOS = 600  # 10 minutos entre revisiones

    while True:
        try:
            response = requests.get(
                URL_LIVE, headers=HEADERS, params={"live": "all"}, timeout=10
            )
            if response.status_code == 200:
                partidos = response.json().get("response", [])
                candidatos_validos = []

                for item in partidos:
                    fixture_id = item["fixture"]["id"]
                    if fixture_id in alertas_disparadas:
                        continue

                    minuto = item["fixture"]["status"]["elapsed"] or 0
                    goles_h = item["goals"]["home"] or 0
                    goles_a = item["goals"]["away"] or 0

                    if 46 <= minuto <= 78 and (goles_h + goles_a) == 0:
                        candidatos_validos.append((fixture_id, item, minuto))

                # Evaluamos máximo 3 candidatos por ciclo para no agotar la cuota
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
                    if es_alerta:
                        guardar_alerta(
                            fixture_id,
                            home_name,
                            away_name,
                            league_name,
                            minuto,
                            equipo,
                        )
                        enviar_alerta_telegram(
                            home_name,
                            away_name,
                            league_name,
                            minuto,
                            equipo,
                        )
                        alertas_disparadas.add(fixture_id)
        except Exception as e:
            print(f"Error en escaneo: {e}")

        time.sleep(INTERVALO_SEGUNDOS)


# ==========================================
# INTERFAZ WEB HTML
# ==========================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Panel de Alertas - Over 0.5 Goals</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0f172a; color: #f8fafc; margin: 0; padding: 20px; }
        .container { max-width: 1000px; margin: 0 auto; }
        .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #334155; padding-bottom: 15px; margin-bottom: 25px; }
        h1 { margin: 0; font-size: 24px; color: #38bdf8; }
        .status { background: #166534; color: #4ade80; padding: 6px 12px; border-radius: 20px; font-size: 14px; font-weight: bold; }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
        .card { background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 20px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3); }
        .card-header { font-size: 12px; color: #94a3b8; margin-bottom: 10px; display: flex; justify-content: space-between; }
        .match-title { font-size: 18px; font-weight: bold; color: #ffffff; margin-bottom: 15px; text-align: center; }
        .badge { background: #0284c7; color: white; padding: 4px 8px; border-radius: 6px; font-size: 12px; display: inline-block; margin-top: 5px; }
        .footer-card { margin-top: 15px; font-size: 12px; color: #64748b; text-align: right; }
    </style>
    <script>
        setInterval(() => {
            fetch('/api/alertas')
                .then(res => res.json())
                .then(data => {
                    const grid = document.getElementById('alertas-grid');
                    if (data.length === 0) {
                        grid.innerHTML = '<p style="color: #64748b;">No hay alertas registradas aún. Escaneando en vivo...</p>';
                        return;
                    }
                    grid.innerHTML = data.map(a => `
                        <div class="card">
                            <div class="card-header">
                                <span>🏆 ${a.liga}</span>
                                <span>⏱️ Min ${a.minuto}'</span>
                            </div>
                            <div class="match-title">${a.equipo_local} vs ${a.equipo_visita}</div>
                            <div>🔥 Cumple: <span class="badge">${a.equipo_cumple}</span></div>
                            <div class="footer-card">📅 ${a.fecha_hora}</div>
                        </div>
                    `).join('');
                });
        }, 5000);
    </script>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⚽ BOT DE ALERTAS OVER 0.5 GOALS</h1>
            <div class="status">● SISTEMA EN VIVO</div>
        </div>
        <h2>🚨 Alertas Detectadas</h2>
        <div id="alertas-grid" class="grid">
            <p style="color: #64748b;">Cargando alertas en vivo...</p>
        </div>
    </div>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route("/api/alertas")
def api_alertas():
    return jsonify(obtener_alertas())


if __name__ == "__main__":
    inicializar_db()

    hilo_bot = threading.Thread(target=bucle_escaneo, daemon=True)
    hilo_bot.start()

    print("🚀 Servidor Web iniciado en http://127.0.0.1:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)