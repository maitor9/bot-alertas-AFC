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
TELEGRAM_CHAT_ID = "PEGA_AQUI_TU_CHAT_ID"

alertas_disparadas = set()


def enviar_alerta_telegram(
    home_name, away_name, league_name, minuto, equipo_cumple
):
    if (
        TELEGRAM_TOKEN == "PEGA_AQUI_TU_TELEGRAM_TOKEN"
        or not TELEGRAM_TOKEN
        or TELEGRAM_CHAT_ID == "PEGA_AQUI_TU_CHAT_ID"
    ):
        return

    mensaje = (
        f"🚨 <b>¡ALERTA AFC OVER 0.5 GOALS!</b> 🚨\n\n"
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
    INTERVALO_SEGUNDOS = 600

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
# 🎨 DISEÑO NUEVO, MODERNO Y LLAMATIVO
# ==========================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AFC Bot de Alertas - Over 0.5 Goals</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-gradient: linear-gradient(135deg, #0b0f19 0%, #111827 50%, #070a12 100%);
            --card-bg: rgba(17, 24, 39, 0.75);
            --neon-accent: #38bdf8;
            --neon-glow: rgba(56, 189, 248, 0.35);
            --green-glow: #10b981;
            --text-main: #f8fafc;
            --text-sub: #94a3b8;
        }

        body {
            font-family: 'Outfit', sans-serif;
            background: var(--bg-gradient);
            color: var(--text-main);
            margin: 0;
            padding: 30px 15px;
            min-height: 100vh;
        }

        .container {
            max-width: 1100px;
            margin: 0 auto;
        }

        /* HEADER ULTRA MODERNO */
        .header {
            background: rgba(15, 23, 42, 0.6);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 20px;
            padding: 25px 35px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5);
            margin-bottom: 35px;
        }

        .logo-area {
            display: flex;
            align-items: center;
            gap: 15px;
        }

        .logo-icon {
            font-size: 32px;
            background: linear-gradient(135deg, #38bdf8, #818cf8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            filter: drop-shadow(0 0 10px var(--neon-glow));
        }

        h1 {
            margin: 0;
            font-size: 28px;
            font-weight: 800;
            letter-spacing: -0.5px;
            background: linear-gradient(90deg, #ffffff, #cbd5e1);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .subtitle {
            font-size: 13px;
            color: var(--neon-accent);
            text-transform: uppercase;
            letter-spacing: 1.5px;
            font-weight: 600;
            margin-top: 4px;
        }

        .status-badge {
            background: rgba(16, 185, 129, 0.12);
            border: 1px solid rgba(16, 185, 129, 0.3);
            color: var(--green-glow);
            padding: 8px 18px;
            border-radius: 30px;
            font-size: 13px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
            box-shadow: 0 0 15px rgba(16, 185, 129, 0.2);
        }

        .pulse-dot {
            width: 8px;
            height: 8px;
            background-color: var(--green-glow);
            border-radius: 50%;
            box-shadow: 0 0 8px var(--green-glow);
            animation: pulse 1.8s infinite;
        }

        @keyframes pulse {
            0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
            70% { transform: scale(1); box-shadow: 0 0 0 10px rgba(16, 185, 129, 0); }
            100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
        }

        .section-title {
            font-size: 20px;
            font-weight: 600;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
            color: #e2e8f0;
        }

        /* GRID Y TARJETAS FUTURISTAS */
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 25px;
        }

        .card {
            background: var(--card-bg);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.07);
            border-radius: 18px;
            padding: 22px;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }

        .card::before {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 3px;
            background: linear-gradient(90deg, #38bdf8, #818cf8);
            opacity: 0.8;
        }

        .card:hover {
            transform: translateY(-5px);
            border-color: rgba(56, 189, 248, 0.4);
            box-shadow: 0 12px 30px rgba(0, 0, 0, 0.4), 0 0 20px var(--neon-glow);
        }

        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 12px;
            color: var(--text-sub);
            margin-bottom: 15px;
        }

        .league-name {
            font-weight: 600;
            color: #cbd5e1;
            background: rgba(255, 255, 255, 0.05);
            padding: 4px 10px;
            border-radius: 6px;
        }

        .minute-tag {
            color: #f59e0b;
            font-weight: 800;
            background: rgba(245, 158, 11, 0.1);
            padding: 4px 8px;
            border-radius: 6px;
            border: 1px solid rgba(245, 158, 11, 0.2);
        }

        .match-title {
            font-size: 19px;
            font-weight: 700;
            color: #ffffff;
            text-align: center;
            margin: 15px 0 20px 0;
            line-height: 1.3;
        }

        .team-fulfilled {
            background: rgba(56, 189, 248, 0.08);
            border: 1px solid rgba(56, 189, 248, 0.25);
            padding: 10px 14px;
            border-radius: 12px;
            font-size: 13px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            color: #e2e8f0;
        }

        .badge-team {
            background: linear-gradient(135deg, #0284c7, #2563eb);
            color: #ffffff;
            font-weight: 700;
            padding: 4px 10px;
            border-radius: 8px;
            font-size: 12px;
            box-shadow: 0 2px 8px rgba(2, 132, 199, 0.4);
        }

        .footer-card {
            margin-top: 18px;
            font-size: 11px;
            color: #64748b;
            text-align: right;
            border-top: 1px solid rgba(255, 255, 255, 0.05);
            padding-top: 10px;
        }

        .empty-state {
            grid-column: 1 / -1;
            text-align: center;
            padding: 50px 20px;
            background: var(--card-bg);
            border-radius: 18px;
            border: 1px dashed rgba(255, 255, 255, 0.1);
            color: var(--text-sub);
        }

        @media (max-width: 600px) {
            .header { flex-direction: column; gap: 15px; text-align: center; }
            .logo-area { flex-direction: column; }
        }
    </style>
    <script>
        function cargarAlertas() {
            fetch('/api/alertas')
                .then(res => res.json())
                .then(data => {
                    const grid = document.getElementById('alertas-grid');
                    if (!data || data.length === 0) {
                        grid.innerHTML = `
                            <div class="empty-state">
                                <h3>🔎 Rastreo Continuo Activado</h3>
                                <p>Escaneando partidos en vivo en el mundo cada 10 minutos...</p>
                            </div>`;
                        return;
                    }
                    grid.innerHTML = data.map(a => `
                        <div class="card">
                            <div class="card-header">
                                <span class="league-name">🏆 ${a.liga}</span>
                                <span class="minute-tag">⏱️ ${a.minuto}'</span>
                            </div>
                            <div class="match-title">${a.equipo_local} vs ${a.equipo_visita}</div>
                            <div class="team-fulfilled">
                                <span>Presión Detectada:</span>
                                <span class="badge-team">${a.equipo_cumple}</span>
                            </div>
                            <div class="footer-card">📅 ${a.fecha_hora}</div>
                        </div>
                    `).join('');
                })
                .catch(err => {
                    console.error('Error cargando alertas:', err);
                });
        }

        // Ejecutar inmediatamente al cargar la página
        document.addEventListener('DOMContentLoaded', cargarAlertas);
        
        // Consultar automáticamente cada 5 segundos
        setInterval(cargarAlertas, 5000);
    </script>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo-area">
                <div class="logo-icon">⚽</div>
                <div>
                    <h1>AFC Bot de Alertas</h1>
                    <div class="subtitle">Estrategia Over 0.5 Goals en Vivo</div>
                </div>
            </div>
            <div class="status-badge">
                <div class="pulse-dot"></div>
                SISTEMA EN VIVO
            </div>
        </div>

        <div class="section-title">
            🚨 Últimas Alertas Detectadas
        </div>

        <div id="alertas-grid" class="grid">
            <div class="empty-state">
                <p>Cargando panel de control...</p>
            </div>
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
